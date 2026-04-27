import streamlit as st
import pandas as pd
import io

st.set_page_config(
    page_title="Calculadora de Custos RCS & SMS",
    page_icon="📱",
    layout="wide",
)

PRECO_RCS = 0.105 / 100   # 0,105 centavos = R$ 0,00105
PRECO_SMS = 0.05  / 100   # 0,05 centavos  = R$ 0,0005

def fmt_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_num(v):
    return f"{int(v):,}".replace(",", ".")

def ler_csv(f, sep):
    try:
        return pd.read_csv(f, sep=sep, encoding="utf-8")
    except UnicodeDecodeError:
        f.seek(0)
        return pd.read_csv(f, sep=sep, encoding="latin-1")

def detectar_e_ler(f):
    f.seek(0)
    df = ler_csv(f, sep=";")
    if len(df.columns) > 1:
        return df
    f.seek(0)
    df = ler_csv(f, sep="\t")
    if len(df.columns) > 1:
        return df
    return None

def processar_rcs(df):
    df = df.copy()
    df["TOTAL RCS ENVIADO"] = pd.to_numeric(df["TOTAL RCS ENVIADO"], errors="coerce").fillna(0).astype(int)
    df["TOTAL SMS ENVIADO"] = pd.to_numeric(df["TOTAL SMS ENVIADO"], errors="coerce").fillna(0).astype(int)
    df["CUSTO RCS (R$)"]   = (df["TOTAL RCS ENVIADO"] * PRECO_RCS).round(2)
    df["CUSTO SMS (R$)"]   = (df["TOTAL SMS ENVIADO"] * PRECO_SMS).round(2)
    df["CUSTO TOTAL (R$)"] = (df["CUSTO RCS (R$)"] + df["CUSTO SMS (R$)"]).round(2)
    return df

def processar_sms(df):
    df = df.copy()
    mask = df["Conta"].isna() | (df["Conta"].astype(str).str.strip() == "")
    df_puro = df[mask].copy()
    df_puro["Quantidade"]     = pd.to_numeric(df_puro["Quantidade"], errors="coerce").fillna(0).astype(int)
    df_puro["CUSTO SMS (R$)"] = (df_puro["Quantidade"] * PRECO_SMS).round(2)
    return df_puro, len(df), len(df) - len(df_puro)

# ── Cabeçalho ────────────────────────────────────────────────────────────────
st.title("📱 Calculadora de Custos — RCS & SMS")
st.markdown("""
| Tipo | Custo unitário |
|------|---------------|
| RCS  | 0,105 centavos → R$ 0,00105 / mensagem |
| SMS  | 0,05 centavos  → R$ 0,0005  / mensagem |

Faça upload de **um ou mais arquivos** — o tipo de cada um é detectado automaticamente.
""")
st.divider()

# ── Upload múltiplo ───────────────────────────────────────────────────────────
arquivos = st.file_uploader(
    "Selecione os arquivos CSV (relatório RCS e/ou sintético SMS)",
    type=["csv"],
    accept_multiple_files=True,
)

if not arquivos:
    st.info("⬆️ Aguardando upload dos arquivos CSV...")
    st.stop()

# ── Acumuladores globais ──────────────────────────────────────────────────────
g_rcs_msgs = g_sms_rcs_msgs = g_sms_puro_msgs = 0
g_custo_rcs = g_custo_sms_rcs = g_custo_sms_puro = 0.0
todas_linhas_export = []  # para download consolidado

# ── Processar cada arquivo ────────────────────────────────────────────────────
for arq in arquivos:
    df = detectar_e_ler(arq)
    if df is None:
        st.error(f"❌ `{arq.name}` — não foi possível detectar o separador.")
        continue

    with st.expander(f"📄 {arq.name}", expanded=True):

        # ── RCS ───────────────────────────────────────────────────────────────
        if {"TOTAL RCS ENVIADO", "TOTAL SMS ENVIADO"}.issubset(df.columns):
            st.caption("🟢 Tipo: **Relatório RCS**")
            df = processar_rcs(df)

            rcs_msgs  = int(df["TOTAL RCS ENVIADO"].sum())
            sms_msgs  = int(df["TOTAL SMS ENVIADO"].sum())
            custo_rcs = round(df["CUSTO RCS (R$)"].sum(), 2)
            custo_sms = round(df["CUSTO SMS (R$)"].sum(), 2)
            custo_tot = round(custo_rcs + custo_sms, 2)

            g_rcs_msgs     += rcs_msgs
            g_sms_rcs_msgs += sms_msgs
            g_custo_rcs    += custo_rcs
            g_custo_sms_rcs += custo_sms

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("📨 RCS Enviados",  fmt_num(rcs_msgs))
            c2.metric("📩 SMS Enviados",  fmt_num(sms_msgs))
            c3.metric("💸 Custo RCS",     fmt_brl(custo_rcs))
            c4.metric("💸 Custo SMS",     fmt_brl(custo_sms))
            c5.metric("💰 Total arquivo", fmt_brl(custo_tot))

            cols = [c for c in ["NOME CAMPANHA", "DATA CRIACAO DA CAMPANHA", "CONTA"] if c in df.columns]
            cols += ["TOTAL RCS ENVIADO", "CUSTO RCS (R$)", "TOTAL SMS ENVIADO", "CUSTO SMS (R$)", "CUSTO TOTAL (R$)"]
            st.dataframe(
                df[cols].style.format({
                    "CUSTO RCS (R$)": fmt_brl,
                    "CUSTO SMS (R$)": fmt_brl,
                    "CUSTO TOTAL (R$)": fmt_brl,
                }),
                use_container_width=True, hide_index=True,
            )
            df["_arquivo"] = arq.name
            df["_tipo"]    = "RCS"
            todas_linhas_export.append(df[["_arquivo", "_tipo"] + cols])

        # ── SMS Sintético ─────────────────────────────────────────────────────
        elif {"Conta", "Quantidade"}.issubset(df.columns):
            st.caption("🔵 Tipo: **Sintético SMS** — apenas linhas com Conta vazia")
            df_puro, total_linhas, ignoradas = processar_sms(df)

            sms_msgs  = int(df_puro["Quantidade"].sum())
            custo_sms = round(df_puro["CUSTO SMS (R$)"].sum(), 2)

            g_sms_puro_msgs  += sms_msgs
            g_custo_sms_puro += custo_sms

            st.caption(
                f"📋 {total_linhas} linhas · ✅ {len(df_puro)} Conta vazia · "
                f"⏭️ {ignoradas} ignoradas (já no RCS)"
            )

            c1, c2 = st.columns(2)
            c1.metric("📩 SMS puro (Conta vazia)", fmt_num(sms_msgs))
            c2.metric("💰 Custo SMS",              fmt_brl(custo_sms))

            if len(df_puro) > 0:
                cols = [c for c in ["Mailing", "Data", "Usuario", "Quantidade", "Enviadas", "CUSTO SMS (R$)"] if c in df_puro.columns]
                st.dataframe(
                    df_puro[cols].style.format({"CUSTO SMS (R$)": fmt_brl}),
                    use_container_width=True, hide_index=True,
                )
                df_puro["_arquivo"] = arq.name
                df_puro["_tipo"]    = "SMS"
                todas_linhas_export.append(df_puro[["_arquivo", "_tipo"] + cols])
            else:
                st.warning("⚠️ Nenhuma linha com Conta vazia encontrada.")

        # ── Formato desconhecido ──────────────────────────────────────────────
        else:
            st.error(
                f"Formato não reconhecido. Colunas encontradas: `{', '.join(df.columns.tolist())}`"
            )

st.divider()

# ── Resumo consolidado ────────────────────────────────────────────────────────
st.subheader("📊 Resumo Consolidado — Todos os Arquivos")

g_custo_sms_total = round(g_custo_sms_rcs + g_custo_sms_puro, 2)
g_custo_geral     = round(g_custo_rcs + g_custo_sms_total, 2)
g_sms_total       = g_sms_rcs_msgs + g_sms_puro_msgs

c1, c2, c3 = st.columns(3)
c4, c5, c6 = st.columns(3)

c1.metric("📨 Total Msgs RCS",         fmt_num(g_rcs_msgs))
c2.metric("📩 Total Msgs SMS",         fmt_num(g_sms_total),
          help=f"Via RCS: {fmt_num(g_sms_rcs_msgs)} · SMS puro: {fmt_num(g_sms_puro_msgs)}")
c3.metric("📬 Total Mensagens",        fmt_num(g_rcs_msgs + g_sms_total))
c4.metric("💸 Custo RCS",              fmt_brl(g_custo_rcs))
c5.metric("💸 Custo SMS",              fmt_brl(g_custo_sms_total),
          help=f"Via RCS: {fmt_brl(g_custo_sms_rcs)} · SMS puro: {fmt_brl(g_custo_sms_puro)}")
c6.metric("💰 Custo Total Geral",      fmt_brl(g_custo_geral))

# ── Download consolidado ──────────────────────────────────────────────────────
if todas_linhas_export:
    st.divider()
    df_export = pd.concat(todas_linhas_export, ignore_index=True)
    buf = io.BytesIO()
    df_export.to_csv(buf, index=False, sep=";", encoding="utf-8-sig")
    buf.seek(0)
    st.download_button("📥 Baixar CSV consolidado com custos", buf, "custos_consolidado.csv", "text/csv")

st.divider()
st.caption(
    "Preços: RCS = 0,105 centavos/msg (R$ 0,00105) · SMS = 0,05 centavos/msg (R$ 0,0005) · "
    "Valores arredondados para 2 casas decimais"
)
