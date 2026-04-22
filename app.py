import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Dashboard Interativo DRE", layout="wide")

# LOGIN
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


from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def gerar_pdf(df_pivot):
    pdf_file = "dashboard.pdf"
    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(pdf_file)
    elementos = []

    # Título
    elementos.append(Paragraph("Relatório DRE", styles["Title"]))
    elementos.append(Spacer(1, 12))

    # Cabeçalho da tabela
    dados = [["Mês", "Realizado", "Orçado", "Diferença", "Status"]]

    # Linhas
    for _, row in df_pivot.iterrows():
        dados.append([
            row["Mes_Nome"],
            f"{row['Realizado']:.2f}",
            f"{row['Orçado']:.2f}",
            f"{row['Diferença']:.2f}",
            row["Status"]
        ])

    # Criar tabela
    tabela = Table(dados)

    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
    ]))

    elementos.append(tabela)

    doc.build(elementos)

    return pdf_file

st.title("Dashboard Interativo de Análise de Dados")

with st.sidebar:
    st.header("Configurações")
    arquivo = st.file_uploader("Envie um arquivo Excel", type=["xlsx"])

if arquivo is not None:
    df = carregar_dados(arquivo)
else:
    df = carregar_dados(ARQUIVO_PADRAO)

st.subheader("Pré-visualização dos dados")
st.dataframe(df.head(20), use_container_width=True)

# FILTROS
st.sidebar.header("Filtros")

tipos = st.sidebar.multiselect("Tipo", df["Tipo"].unique(), default=df["Tipo"].unique())
anos = st.sidebar.multiselect("Ano", df["Ano"].unique(), default=df["Ano"].unique())
meses = st.sidebar.multiselect(
    "Mês",
    df["Mes"].unique(),
    default=df["Mes"].unique()
)

valor_min, valor_max = st.sidebar.slider(
    "Faixa de Valor",
    float(df["Valor"].min()),
    float(df["Valor"].max()),
    (float(df["Valor"].min()), float(df["Valor"].max()))
)

df_f = df[
    (df["Tipo"].isin(tipos)) &
    (df["Ano"].isin(anos)) &
    (df["Mes"].isin(meses)) &
    (df["Valor"] >= valor_min) &
    (df["Valor"] <= valor_max)
]

# MÉTRICAS
col1, col2, col3 = st.columns(3)

col1.metric("Total", f"R$ {df_f['Valor'].sum():,.0f}")
col2.metric("Média", f"R$ {df_f['Valor'].mean():,.0f}")
col3.metric("Registros", len(df_f))

# GRÁFICO PRINCIPAL
st.subheader("Gráfico Geral")

fig = px.bar(df_f, x="Mes_Nome", y="Valor", color="Tipo", barmode="group")
st.plotly_chart(fig, use_container_width=True)

# COMPARAÇÃO REAL X ORÇADO
st.subheader("Comparação Real x Orçado")

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

# DETECÇÃO DE PREJUÍZO
st.subheader("Análise de Desempenho")

df_pivot = df_f.pivot_table(
    index="Mes_Nome",
    columns="Tipo",
    values="Valor",
    aggfunc="sum"
).reset_index()

df_pivot["Diferença"] = df_pivot["Realizado"] - df_pivot["Orçado"]

def status(valor):
    return "🔴 Prejuízo" if valor < 0 else "🟢 OK"

df_pivot["Status"] = df_pivot["Diferença"].apply(status)

st.dataframe(df_pivot, use_container_width=True)

# EXPORTAR PDF
if st.button("Exportar PDF"):
    pdf_path = gerar_pdf(df_pivot)

    with open(pdf_path, "rb") as f:
        st.download_button(
            "Baixar PDF",
            f,
            file_name="dashboard.pdf"
        )

st.dataframe(df_pivot, use_container_width=True)

# EXPORTAR CSV

csv = df_pivot.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Baixar tabela em CSV",
    data=csv,
    file_name="resumo.csv",
    mime="text/csv",
)
