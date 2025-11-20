import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime

import base64

def set_background(image_file):
    with open(image_file, "rb") as img:
        encoded = base64.b64encode(img.read()).decode()
    css = f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpeg;base64,{encoded}");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
        opacity: 0.98;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# URL do Google Sheets exportado como CSV
GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/1OT7_kwu1RqUEuOmf_GNq9Wl7ftc60OjwyX5omXwCTTI/export?format=csv"

# ======================================
# FUNÇÕES
# ======================================

def hash_arquivo(url):
    """Cria um hash do conteúdo do CSV para detectar mudanças"""
    df = pd.read_csv(url)
    return hashlib.md5(pd.util.hash_pandas_object(df, index=True).values).hexdigest()

@st.cache_data(ttl=None, persist=True, show_spinner=False)
def carregar_dados(url, hash_atual=None):
    """
    Carrega dados do Google Sheets CSV.
    Recarrega apenas se o hash mudar (planilha atualizada).
    """
    df = pd.read_csv(
        url,
        usecols=lambda c: c.upper() in ['FORNECEDOR','PRODUTOS','QUANT','UNIDADE','PREÇO','TOTAL','DATA','NFE']
    )
    df.columns = df.columns.str.upper().str.strip()

    # --- Corrige datas (formato datetime) ---
    if 'DATA' in df.columns:
        df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce', dayfirst=True)

    # --- Corrige colunas de moeda ---
    for col in ['PREÇO', 'TOTAL']:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace('R$', '', regex=False)
                .str.replace(' ', '', regex=False)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

def pesquisar_produto(df, termo):
    if not termo:
        return pd.DataFrame()
    mask = df['PRODUTOS'].fillna('').str.contains(termo, case=False, na=False)
    return df.loc[mask]

def formatar_tabela(df):
    """Formata datas e valores no padrão brasileiro para exibição"""
    if df.empty:
        return df
    df_form = df.copy()

    # Formata colunas de moeda
    for col in ['PREÇO', 'TOTAL']:
        if col in df_form.columns:
            df_form[col] = pd.to_numeric(df_form[col], errors='coerce')
            df_form[col] = df_form[col].apply(
                lambda x: f"R$ {x:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')
                if pd.notnull(x) else ""
            )

    # Garante formato de data dd/mm/aaaa
    if 'DATA' in df_form.columns:
        df_form['DATA'] = pd.to_datetime(df_form['DATA'], errors='coerce', dayfirst=True)
        df_form['DATA'] = df_form['DATA'].apply(
            lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else ""
        )

    return df_form

# ======================================
# INTERFACE STREAMLIT
# ======================================

def app():
    st.set_page_config(page_title='Pesquisa de Produtos', layout='centered')
    set_background("zero_logo.jpeg")
    st.title('📦 Controle de Entradas e Pesquisa de Produtos')

    # Spinner enquanto carrega
    with st.spinner('Carregando dados...'):
        hash_atual = hash_arquivo(GOOGLE_SHEET_CSV)
        dados = carregar_dados(GOOGLE_SHEET_CSV, hash_atual)

    # ----------------------------
    # FILTRO POR DATA
    # ----------------------------
    st.subheader("🔎 Filtro por Data de Chegada")
    data_filtro = st.date_input("Selecione a data:", datetime.today())

    if st.button("Filtrar por Data"):
        data_selecionada = pd.to_datetime(data_filtro)
        filtrado = dados[dados['DATA'] == data_selecionada]

        if not filtrado.empty:
            total_geral = filtrado['TOTAL'].sum()
            st.success(f"Foram encontrados {len(filtrado)} produtos no dia {data_filtro.strftime('%d/%m/%Y')}.")
            st.write(f"💰 **Total geral do dia:** R$ {total_geral:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.'))
            st.dataframe(formatar_tabela(filtrado), use_container_width=True)
        else:
            st.warning(f"Nenhum produto encontrado em {data_filtro.strftime('%d/%m/%Y')}.")

    st.divider()

    # ----------------------------
    # PESQUISA POR PRODUTO
    # ----------------------------
    st.subheader("🔍 Pesquisa por Nome do Produto")
    produto = st.text_input('Digite o nome do produto para pesquisar:')

    if st.button('Pesquisar Produto'):
        resultado = pesquisar_produto(dados, produto)

        if not resultado.empty:
            st.success(f'{len(resultado)} resultado(s) encontrado(s).')
            st.dataframe(formatar_tabela(resultado.tail(5)), use_container_width=True)
        else:
            st.warning('Nenhum produto encontrado.')

    st.caption(f"📄 Total de linhas carregadas: {len(dados):,}")

if __name__ == "__main__":
    app()
