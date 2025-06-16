
"""
Corpus Compass v1.1 - Aplicação Web Completa
"""
import os
import pandas as pd
import json
import time
import streamlit as st
import tempfile
from langchain_google_genai import GoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader

# configurações iniciais do Streamlit
st.set_page_config(
    page_title="Corpus Compass",
    page_icon="💡",
    layout="wide"
)

#prompt para o modelo LLM
PROMPT_FICHAMENTO_JSON = """
Sua tarefa é atuar como um pesquisador assistente e extrair dados estruturados de um artigo científico de qualquer área.
Analise o TEXTO DO ARTIGO fornecido e retorne um objeto JSON válido contendo as seguintes chaves:
- "titulo_artigo": (String) O título completo e exato do artigo.
- "autores": (Lista de Strings) Uma lista com os nomes de todos os autores.
- "ano_publicacao": (String) O ano de publicação do artigo.
- "resumo_ia": (String) Um resumo conciso do artigo em 3 a 4 frases, focando no problema, metodologia e conclusão.
- "palavras_chave_ia": (Lista de Strings) Uma lista com 5 a 10 palavras-chave ou frases-chave técnicas.
- "metodologia_principal": (String) Descreva de forma concisa (1 a 2 frases) a principal metodologia.
- "grande_area_conhecimento": (String) Identifique a grande área e o sub-campo do artigo (ex: 'Direito / Direito Penal', 'Biologia / Ornitologia').

TEXTO DO ARTIGO:
{texto_documento}

OBJETO JSON COM OS DADOS EXTRAÍDOS:
"""

#função para inicializar o modelo LLM com a chave de API
@st.cache_resource
def get_llm(api_key):
    """Inicializa e retorna o modelo LLM."""
    os.environ['GOOGLE_API_KEY'] = api_key
    return GoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.0)

def extrair_dados_com_json(llm, texto_documento):
    """Faz uma única chamada à API pedindo um JSON com todos os dados."""
    prompt_formatado = PROMPT_FICHAMENTO_JSON.format(texto_documento=texto_documento[:30000])
    try:
        resposta_llm = llm.invoke(prompt_formatado)
        resposta_limpa = resposta_llm.strip().replace('```json', '').replace('```', '')
        return json.loads(resposta_limpa)
    except json.JSONDecodeError:
        st.warning(f"O modelo não retornou um JSON válido para um dos artigos. A resposta foi: {resposta_llm[:200]}...")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro na API: {e}")
        return None

#titulo
st.title("💡 Corpus Compass")
st.subheader("Analisador de artigos científicos com Inteligência Artificial")


#abas
tab_analisador, tab_como_funciona, tab_sobre = st.tabs(["**Analisador**", "**Como Funciona**", "**Quem sou eu?**"])


#conteúdo aba 1: Analisador
with tab_analisador:
    st.header("Análise de Artigos")
    st.markdown("Faça o upload de um ou mais artigos em PDF e receba uma planilha Excel com um resumo estruturado, extraído por Inteligência Artificial.")

    #barra laetral 
    with st.sidebar:
        st.header("Configurações")
        api_key = st.text_input("Sua Chave de API do Google AI", type="password", help="É necessário ter uma chave de API do Google AI para usar a aplicação.")
        st.markdown("[Obtenha sua chave de API aqui](https://aistudio.google.com/)")

    #area upload de arquivos
    uploaded_files = st.file_uploader(
        "Escolha os arquivos PDF para analisar",
        type="pdf",
        accept_multiple_files=True,
        help="Você pode arrastar e soltar vários arquivos aqui."
    )

    #botao iniciar analise
    if st.button("Analisar Artigos", disabled=(not uploaded_files or not api_key)):
        if not api_key:
            st.error("Por favor, insira sua chave de API na barra lateral para continuar.")
        elif not uploaded_files:
            st.warning("Por favor, faça o upload de pelo menos um arquivo PDF.")
        else:
            dados_compilados = []
            llm = get_llm(api_key)
            barra_progresso = st.progress(0, text="Iniciando análise...")

            for i, uploaded_file in enumerate(uploaded_files):
                nome_arquivo = uploaded_file.name
                texto_progresso = f"Processando artigo {i+1}/{len(uploaded_files)}: {nome_arquivo}"
                barra_progresso.progress((i) / len(uploaded_files), text=texto_progresso)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    caminho_tmp = tmp_file.name

                try:
                    loader = PyPDFLoader(caminho_tmp)
                    documento = loader.load()
                    texto_completo = " ".join(page.page_content for page in documento)

                    if texto_completo.strip():
                        dados_extraidos = extrair_dados_com_json(llm, texto_completo)
                        if dados_extraidos:
                            dados_extraidos['arquivo'] = nome_arquivo
                            dados_compilados.append(dados_extraidos)
                    else:
                        st.warning(f"Nenhum texto útil foi extraído de '{nome_arquivo}'.")

                except Exception as e:
                    st.error(f"Ocorreu um erro crítico ao processar '{nome_arquivo}': {e}")
                finally:
                    os.remove(caminho_tmp)

            barra_progresso.progress(1.0, text="Análise concluída!")
            st.session_state['df_resultado'] = pd.DataFrame(dados_compilados)

    #resultado e download
    if 'df_resultado' in st.session_state and not st.session_state['df_resultado'].empty:
        st.success("Sua análise está pronta!")
        df = st.session_state['df_resultado']
        
        ordem_colunas = ['arquivo', 'titulo_artigo', 'autores', 'ano_publicacao', 'grande_area_conhecimento', 'resumo_ia', 'palavras_chave_ia', 'metodologia_principal']
        for col in ordem_colunas:
            if col not in df.columns:
                df[col] = "Não encontrado"
        df_final = df[ordem_colunas]

        st.dataframe(df_final)

        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Fichamentos')
        
        excel_bytes = output.getvalue()

        st.download_button(
            label="Baixar Planilha Excel com os Fichamentos",
            data=excel_bytes,
            file_name="relatorio_fichamentos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

#aba 2: Como Funciona
with tab_como_funciona:
    st.header("Como Funciona?")
    st.markdown("""
    Esta ferramenta utiliza o poder de Grandes Modelos de Linguagem (LLMs), especificamente o **Google Gemini**, para realizar uma leitura inteligente e contextual de artigos científicos.
    
    O processo funciona em três passos simples:

    **1. Envio e Leitura (📤 Upload)**
    * Quando você faz o upload de um PDF, o sistema extrai todo o texto do arquivo, preparando-o para a análise.

    **2. Análise com IA (🧠 Processamento)**
    * O texto completo de cada artigo é enviado para o Gemini com um conjunto de instruções precisas (um "prompt").
    * Pedimos à IA que atue como um pesquisador assistente e extraia dados específicos, como título, autores, resumo, metodologia e palavras-chave. A IA não "inventa" informações, ela as localiza e estrutura a partir do texto fornecido, evitando as famosas "alucinações" comuns em modelos de linguagem.

    **3. Geração do Relatório (📊 Download)**
    * Todos os dados estruturados de cada artigo são compilados em uma tabela organizada.
    * Essa tabela é então convertida em uma planilha Excel, pronta para você baixar e utilizar em sua pesquisa, economizando horas de trabalho manua!.
    """)

#aba 3: Quem sou eu?
with tab_sobre:
    st.header("Quem sou eu?")

    # --- INSTRUÇÃO: Substitua o link da imagem e o texto abaixo ---
    
    # Coloque sua foto na mesma pasta do script e mude o nome do arquivo aqui
    # OU coloque um link para uma foto online
    caminho_da_foto = "eu.jpg" # <--- SUBSTITUA ESTE LINK

    col1, col2 = st.columns([1, 3])

    with col1:
        st.image(caminho_da_foto, caption="Jade Pereira", width=200)

    with col2:
        # Edite este texto com a sua apresentação
        st.markdown("""
        ### Jade Pereira
        
        Olá! Eu sou estudante de Licenciatura em Ciências Biológicas e uma entusiasta da aplicação de novas tecnologias para acelerar e aprofundar a pesquisa científica.
        
        Este projeto, **Corpus Compass**, nasceu da minha própria experiência com tarefa de realizar revisões de literatura. Meu objetivo foi criar uma ferramenta intuitiva que pudesse automatizar o trabalho inicial de fichamento, liberando tempo para a parte mais importante: a análise crítica e a geração de novas ideias.
        
        Mas é claro, nenhuma ferramenta substitui o olhar humano. Recomenda-se fortemente que você revise os dados extraídos, especialmente o resumo e as palavras-chave, para garantir que estejam alinhados com o contexto do seu trabalho, beleza?!
        
        Acredito que a união entre a Biologia e a Ciência da Computação tem um potencial imenso para transformar a forma como fazemos ciência.
        """)

    st.markdown("---")
    st.subheader("Contato")
    st.markdown("Tem alguma dúvida, sugestão ou encontrou algum problema? Ficarei feliz em ajudar!")
    st.markdown("📧 **E-mail:** [jade.pereira@ufv.br](mailto:jade.pereira@ufv.br)")
