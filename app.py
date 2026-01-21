import streamlit as st
import pandas as pd
import unicodedata

st.set_page_config(page_title="Relatório de Custos", layout="wide")
st.title("Relatório de Custos por Equipe")

# ==================================================
# Funções auxiliares
# ==================================================

def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8")
    return texto

def identificar_equipe(nome_campanha):
    texto = normalizar_texto(nome_campanha)

    if any(p in texto for p in ["iniciativaprivada", "iniciativa privada", "clt"]):
        return "CLT"
    if any(p in texto for p in ["outbound", "aquisicao", "aquisição"]):
        return "OUTBOUND"
    if any(p in texto for p in ["ativacao", "csativacao", "ativação"]):
        return "ATIVACAO"
    if any(p in texto for p in ["csapp", "app", "aplicativo"]):
        return "CSAPP"
    if any(p in texto for p in ["cp", "inss", "cscp"]):
        return "CP"

    return "OUTROS"

def custo_por_canal(canal):
    canal = str(canal).lower()
    if canal == "sms":
        return 0.047
    if canal == "rcs":
        return 0.105
    return 0.0

# ==================================================
# Upload
# ==================================================

arquivos = st.file_uploader(
    "Envie os arquivos Analytic e/ou Sintético",
    type=["csv"],
    accept_multiple_files=True
)

df_analytic = pd.DataFrame()
sms_sintetico_qtd = 0
sms_sintetico_custo = 0.0

# ==================================================
# Processamento
# ==================================================

if arquivos:
    for arquivo in arquivos:
        nome = arquivo.name.lower()

        # ---------------- ANALYTIC ----------------
        if "analytic" in nome:
            df = pd.read_csv(arquivo, sep=None, engine="python")

            df["STATUS"] = df["STATUS"].str.upper()
            df["CANAL"] = df["CANAL"].str.lower()

            df = df[
                (
                    (df["CANAL"] == "rcs") &
                    (df["STATUS"].isin(["ENTREGUE", "ENVIADO", "LIDO"]))
                )
                |
                (
                    (df["CANAL"] == "sms") &
                    (df["STATUS"].isin(["ENTREGUE", "ENVIADO", "NÃO ENTREGUE"]))
                )
            ]

            if not df.empty:
                df["EQUIPE"] = df["NOME CAMPANHA"].apply(identificar_equipe)
                df["CUSTO"] = df["CANAL"].apply(custo_por_canal)
                df_analytic = pd.concat([df_analytic, df])

        # ---------------- SINTÉTICO ----------------
        if "sintetico" in nome or "sintético" in nome:
            df_sint = pd.read_csv(arquivo, sep="\t")

            df_sint = df_sint[df_sint["Conta"].isna()]

            df_sint["Total De Msg Tarifadas"] = (
                df_sint["Total De Msg Tarifadas"]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .astype(float)
            )

            sms_sintetico_qtd += int(df_sint["Total De Msg Tarifadas"].sum())
            sms_sintetico_custo += sms_sintetico_qtd * 0.047

# ==================================================
# Tabela base segura (SEMPRE EXISTE)
# ==================================================

tabela = pd.DataFrame(columns=[
    "EQUIPE",
    "RCS QUANTIDADE", "RCS CUSTO",
    "SMS QUANTIDADE", "SMS CUSTO"
])

# ==================================================
# Agregação Analytic (se houver)
# ==================================================

if not df_analytic.empty:
    base = (
        df_analytic
        .groupby(["EQUIPE", "CANAL"], as_index=False)
        .agg(
            QUANTIDADE=("CUSTO", "count"),
            CUSTO=("CUSTO", "sum")
        )
    )

    piv = base.pivot(index="EQUIPE", columns="CANAL", values=["QUANTIDADE", "CUSTO"])
    piv = piv.fillna(0)
    piv.columns = [f"{c[1].upper()} {c[0]}" for c in piv.columns]
    piv = piv.reset_index()

    tabela = pd.concat([tabela, piv], ignore_index=True)

# ==================================================
# Garantir colunas SEMPRE
# ==================================================

# ==================================================
# Forçar tipos numéricos (evita erro na Cloud)
# ==================================================

colunas_numericas = [
    "RCS QUANTIDADE", "RCS CUSTO",
    "SMS QUANTIDADE", "SMS CUSTO"
]

for col in colunas_numericas:
    tabela[col] = pd.to_numeric(tabela[col], errors="coerce").fillna(0)


# ==================================================
# Aplicar Sintético (OUTBOUND)
# ==================================================

if sms_sintetico_qtd > 0:
    if "OUTBOUND" in tabela["EQUIPE"].values:
        tabela.loc[tabela["EQUIPE"] == "OUTBOUND", "SMS QUANTIDADE"] += sms_sintetico_qtd
        tabela.loc[tabela["EQUIPE"] == "OUTBOUND", "SMS CUSTO"] += sms_sintetico_custo
    else:
        tabela = pd.concat([
            tabela,
            pd.DataFrame([{
                "EQUIPE": "OUTBOUND",
                "RCS QUANTIDADE": 0,
                "RCS CUSTO": 0,
                "SMS QUANTIDADE": sms_sintetico_qtd,
                "SMS CUSTO": sms_sintetico_custo
            }])
        ], ignore_index=True)

# ==================================================
# Totais
# ==================================================

tabela["Quantidade Total"] = tabela["RCS QUANTIDADE"] + tabela["SMS QUANTIDADE"]
tabela["Custo Total"] = (tabela["RCS CUSTO"] + tabela["SMS CUSTO"]).round(2)

tabela = tabela[
    [
        "EQUIPE",
        "RCS QUANTIDADE", "RCS CUSTO",
        "SMS QUANTIDADE", "SMS CUSTO",
        "Quantidade Total", "Custo Total"
    ]
]

# ==================================================
# Exibição
# ==================================================

st.subheader("Relatório Final")
st.dataframe(tabela)

csv = tabela.to_csv(
    index=False,
    sep=";",
    decimal=","
).encode("utf-8")

st.download_button(
    "📥 Baixar relatório",
    csv,
    file_name="relatorio_final.csv",
    mime="text/csv"
)
