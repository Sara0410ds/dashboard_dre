import pandas as pd
import streamlit as st
import plotly.express as px
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import tempfile

st.set_page_config(page_title="Dashboard Interativo DRE", layout="wide")

# ---------------------------
# LOGIN
# ---------------------------
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    st.title("Login")

    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user == "admin" and senha == "123":
            st.session_state["logado"] = True
            st.rerun()
        else:
            st.error("Login inválido")

    st.stop()

# ---------------------------
# CONFIG
# ---------------------------
ARQUIVO_PADRAO = "DRE 2019.xlsx"

@st.cache_data
def carregar_dados(arquivo):
    plano = pd.read_excel(arquivo, sheet_name="Plano de Contas")
    realizado = pd.read_excel(arquivo, sheet_name="Realizado")
    orcado = pd.read_excel(arquivo, sheet_name="Orçado")

    realizado["Conta"] = realizado["Conta"].astype(str)
    orcado["Conta"] = orcado["Conta"].astype(str)
    plano["Conta"] = plano["Conta"].astype(str)

    realizado["Mês/Ano"] = pd.to_datetime(realizado["Mês/Ano"])
    orcado["Mês/Ano"] = pd.to_datetime(orcado["Mês/Ano"])

    df_real = realizado.merge(plano, on="Conta", how="left")
    df_orc = orcado.merge(plano, on="Conta", how="left")

    df_real["Tipo"] = "Realizado"
    df_orc["Tipo"] = "Orçado"

    df_real = df_real.rename(columns={"Valor Realizado": "Valor"})
    df_orc = df_orc.rename(columns={"Valor Orçado": "Valor"})

    df = pd.concat([df_real, df_orc], ignore_index=True)

    df["Ano"] = df["Mês/Ano"].dt.year
    df["Mes"] = df["Mês/Ano"].dt.month
    df["Mes_Nome"] = df["Mês/Ano"].dt.strftime("%b/%Y")

    return df

# ---------------------------
# PDF (CORRIGIDO)
# ---------------------------
def gerar_pdf(df_pivot, fig_comp):
    styles = getSampleStyleSheet()
    pdf_file = "dashboard.pdf"

    doc = SimpleDocTemplate(pdf_file)
    elementos = []

    # Título
    elementos.append(Paragraph("Relatório DRE", styles["Title"]))
    elementos.append(Spacer(1, 12))

    # Métrica
    total = df_pivot["Realizado"].sum()
    elementos.append(Paragraph(f"Total Realizado: R$ {total:,.2f}", styles["Normal"]))
    elementos.append(Spacer(1, 12))

    # 🔥 EXPORTAÇÃO DO GRÁFICO SEM ERRO
    img_bytes = fig_comp.to_image(format="png")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        with open(tmp.name, "wb") as f:
            f.write(img_bytes)

        elementos.append(Image(tmp.name, width=500, height=300))

    elementos.append(Spacer(1, 12))

    # Tabela
    for _, row in df_pivot.iterrows():
        linha = f"{row['Mes_Nome']} | Dif: {row['Diferença']:.2f} | {row['Status']}"
        elementos.append(Paragraph(linha, styles["Normal"]))

    doc.build(elementos)

    return pdf_file

# ---------------------------
# APP
# ---------------------------
st.title("📊 Dashboard Interativo de Análise de Dados")

with st.sidebar:
    st.header("Configurações")
    arquivo = st.file_uploader("Envie um arquivo Excel", type=["xlsx"])

if arquivo is not None:
    df = carregar_dados(arquivo)
else:
    df = carregar_dados(ARQUIVO_PADRAO)

st.subheader("Pré-visualização dos dados")
st.dataframe(df.head(20), use_container_width=True)

# ---------------------------
# FILTROS
# ---------------------------
st.sidebar.header("Filtros")

tipos = st.sidebar.multiselect("Tipo", df["Tipo"].unique(), default=df["Tipo"].unique())
anos = st.sidebar.multiselect("Ano", df["Ano"].unique(), default=df["Ano"].unique())

df_f = df[(df["Tipo"].isin(tipos)) & (df["Ano"].isin(anos))]

# ---------------------------
# MÉTRICAS
# ---------------------------
col1, col2, col3 = st.columns(3)

col1.metric("Total", f"R$ {df_f['Valor'].sum():,.0f}")
col2.metric("Média", f"R$ {df_f['Valor'].mean():,.0f}")
col3.metric("Registros", len(df_f))

# ---------------------------
# GRÁFICO GERAL
# ---------------------------
st.subheader("📊 Gráfico Geral")

fig = px.bar(df_f, x="Mes_Nome", y="Valor", color="Tipo", barmode="group")
st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# COMPARAÇÃO
# ---------------------------
st.subheader("📊 Comparação Real x Orçado")

df_comp = df_f.groupby(["Mes_Nome", "Tipo"])["Valor"].sum().reset_index()

fig_comp = px.bar(
    df_comp,
    x="Mes_Nome",
    y="Valor",
    color="Tipo",
    barmode="group",
    title="Realizado vs Orçado"
)

st.plotly_chart(fig_comp, use_container_width=True)

# ---------------------------
# ANÁLISE
# ---------------------------
st.subheader("📉 Análise de Desempenho")

df_pivot = df_f.pivot_table(
    index="Mes_Nome",
    columns="Tipo",
    values="Valor",
    aggfunc="sum"
).reset_index()

df_pivot = df_pivot.fillna(0)

df_pivot["Diferença"] = df_pivot["Realizado"] - df_pivot["Orçado"]

def status(valor):
    return "🔴 Prejuízo" if valor < 0 else "🟢 OK"

df_pivot["Status"] = df_pivot["Diferença"].apply(status)

st.dataframe(df_pivot, use_container_width=True)

# ---------------------------
# EXPORTAR PDF
# ---------------------------
if st.button("📄 Exportar PDF"):
    pdf_path = gerar_pdf(df_pivot, fig_comp)

    with open(pdf_path, "rb") as f:
        st.download_button(
            "⬇️ Baixar PDF",
            f,
            file_name="dashboard.pdf"
        )

# ---------------------------
# EXPORTAR CSV
# ---------------------------
csv = df_pivot.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "⬇️ Baixar tabela em CSV",
    data=csv,
    file_name="resumo.csv",
    mime="text/csv",
)
