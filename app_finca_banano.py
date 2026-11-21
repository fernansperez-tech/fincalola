import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pandas as pd
from datetime import datetime
import time
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

st.set_page_config(page_title="Bananera la Lola S.a", page_icon="🍌", layout="centered")

COLORES_CINTA = ["Amarilla", "Morada", "Roja", "Cafe", "Negra", "Verde", "Azul", "Blanca"]
LOTES = [f"Lote {i:02d}" for i in range(1, 15)]
HECTAREAS_LOTE = {
    "Lote 01": 3.9, "Lote 02": 4.6, "Lote 03": 4.8, "Lote 04": 7,
    "Lote 05": 7.4, "Lote 06": 7.3, "Lote 07": 5.1, "Lote 08": 6.4,
    "Lote 09": 8.5, "Lote 10": 7.8, "Lote 11": 7.7, "Lote 12": 6.3,
    "Lote 13": 6, "Lote 14": 3.3
}

PARCELEROS_BASE = [
    "Carracedo Daison",
    "Chiquillo libardo",
    "Fernanadez Luis",
    "Cantillo Pedro",
    "Acosta Yeison",
    "Reales Isaac",
    "Gonzales Jose",
    "Felipe Evenildo",
    "Narvaez Osvaldo",
    "Santiago Oscar",
    "Silva Harold",
    "Pantoja Cesar",
    "Osvaldo Castro",
        
    "Otro (Escribir nombre)"
]

CLAVE_ADMIN = "banano2026"
ID_HOJA = "1WnHs71IMeuz9X9sAtJkNYJbR9QJE2QqAKq37-PGsr-0"
NOMBRE_HOJA = "Hoja 1"

if "cola_offline" not in st.session_state:
    st.session_state.cola_offline = []

def conectar_hoja():
    sec = st.secrets["connections"]["gsheets"]
    llave_privada = sec["private_key"].replace("\\n", "\n")
    prefijo = "https" + chr(58) + "//"
    dominio_g = "googleapis.com"
    info_credenciales = {
        "type": "service_account",
        "project_id": sec["project_id"],
        "private_key_id": sec["private_key_id"],
        "private_key": llave_privada,
        "client_email": sec["client_email"],
        "client_id": sec["client_id"],
        "auth_uri": prefijo + "://google.com",
        "token_uri": prefijo + "oauth2." + dominio_g + "/token",
        "auth_provider_x509_cert_url": prefijo + "www." + dominio_g + "/oauth2/v1/certs",
        "client_x509_cert_url": sec.get("client_x509_cert_url", "")
    }
    alcances = [
        prefijo + "www." + dominio_g + "/auth/spreadsheets",
        prefijo + "www." + dominio_g + "/auth/drive"
    ]
    credenciales = Credentials.from_service_account_info(info_credenciales, scopes=alcances)
    gc = gspread.authorize(credenciales)
    sh = gc.open_by_key(ID_HOJA)
    return sh.worksheet(NOMBRE_HOJA)

def cargar_datos():
    try:
        ws = conectar_hoja()
        datos = ws.get_all_records()
        if not datos:
            return pd.DataFrame(columns=["Fecha", "Hora", "Semana", "Lote", "Parcelero", "Color_Cinta", "Racimos", "Estado"])
        return pd.DataFrame(datos)
    except Exception:
        return pd.DataFrame(columns=["Fecha", "Hora", "Semana", "Lote", "Parcelero", "Color_Cinta", "Racimos", "Estado"])

def agregar_filas(lista_registros):
    ws = conectar_hoja()
    filas = []
    for r in lista_registros:
        filas.append([
            r["Fecha"], r["Hora"], int(r["Semana"]), r["Lote"],
            r["Parcelero"], r["Color_Cinta"], int(r["Racimos"]), r["Estado"]
        ])
    ws.append_rows(filas)

def actualizar_fila_gsheet(num_fila_sheet, nueva_fila_lista):
    ws = conectar_hoja()
    rango = f"A{num_fila_sheet}:H{num_fila_sheet}"
    ws.update(values=[nueva_fila_lista], range_name=rango)

def borrar_fila_gsheet(num_fila_sheet):
    ws = conectar_hoja()
    ws.delete_rows(int(num_fila_sheet))
def borrar_multiples_filas_gsheet(lista_filas_sheet):
    ws = conectar_hoja()
    peticiones = []
    for num_f in sorted(lista_filas_sheet, reverse=True):
        idx_cero = int(num_f) - 1
        peticiones.append({
            "deleteDimension": {
                "range": {
                    "sheetId": ws.id,
                    "dimension": "ROWS",
                    "startIndex": idx_cero,
                    "endIndex": idx_cero + 1
                }
            }
        })
    if peticiones:
        ws.spreadsheet.batch_update({"requests": peticiones})
def cargar_config_proyeccion():
    try:
        sh = conectar_gsheet()
        try:
            ws_p = sh.worksheet("Proyecciones")
        except Exception:
            ws_p = sh.add_worksheet(title="Proyecciones", rows=30, cols=10)
            ws_p.append_row(["Orden", "Semana_Proy", "P12", "P11", "P10", "P9", "Ratio", "Merma", "Fecha_Guardado"])
            return pd.DataFrame()
        datos_p = ws_p.get_all_records()
        return pd.DataFrame(datos_p) if datos_p else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def guardar_config_proyeccion(df_cfg, ratio_val, merma_val):
    sh = conectar_gsheet()
    try:
        ws_p = sh.worksheet("Proyecciones")
    except Exception:
        ws_p = sh.add_worksheet(title="Proyecciones", rows=30, cols=10)
    ws_p.clear()
    ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    filas_ws = [["Orden", "Semana_Proy", "P12", "P11", "P10", "P9", "Ratio", "Merma", "Fecha_Guardado"]]
    for _, r in df_cfg.iterrows():
        filas_ws.append([
            int(r["Orden"]),
            str(r["Semana_Proy"]),
            int(r["% 12+ sem"]),
            int(r["% 11 sem"]),
            int(r["% 10 sem"]),
            int(r["% 9 sem"]),
            float(ratio_val),
            int(merma_val),
            ahora_str
        ])
    ws_p.update("A1", filas_ws)

def procesar_csv_tableta(df_tab, col_lote, col_color, col_fecha=None, col_bruto="Ninguna", col_tara="Ninguna", col_vastago="Ninguna"):
    ahora = datetime.now()
    df_work = df_tab.dropna(subset=[col_lote, col_color]).copy()
    if df_work.empty:
        return []
    if col_fecha and col_fecha != "Usar fecha de hoy":
        df_work["Fecha_Norm"] = pd.to_datetime(df_work[col_fecha], errors="coerce").dt.strftime("%Y-%m-%d").fillna(ahora.strftime("%Y-%m-%d"))
    else:
        df_work["Fecha_Norm"] = ahora.strftime("%Y-%m-%d")

    df_work["Bruto_Num"] = pd.to_numeric(df_work[col_bruto], errors="coerce").fillna(0.0) if col_bruto != "Ninguna" else 0.0
    df_work["Tara_Num"] = pd.to_numeric(df_work[col_tara], errors="coerce").fillna(0.0) if col_tara != "Ninguna" else 0.0
    df_work["Vastago_Num"] = pd.to_numeric(df_work[col_vastago], errors="coerce").fillna(0.0) if col_vastago != "Ninguna" else 0.0

    conteo = df_work.groupby(["Fecha_Norm", col_lote, col_color]).agg(
        Total_Racimos=(col_lote, "size"),
        Suma_Bruto=("Bruto_Num", "sum"),
        Suma_Tara=("Tara_Num", "sum"),
        Suma_Vastago=("Vastago_Num", "sum")
    ).reset_index()

    descuentos = []
    for _, fila in conteo.iterrows():
        lote_raw = str(fila[col_lote]).strip()
        num_lote = "".join(filter(str.isdigit, lote_raw))
        lote_norm = f"Lote {int(num_lote):02d}" if num_lote else lote_raw
        color_norm = str(fila[col_color]).strip().replace("é", "e").replace("É", "E").capitalize()
        cant = int(fila["Total_Racimos"])
        fecha_str = str(fila["Fecha_Norm"])
        try:
            semana_num = datetime.strptime(fecha_str, "%Y-%m-%d").isocalendar().week
        except Exception:
            semana_num = ahora.isocalendar().week
        tara_str = str(round(float(fila["Suma_Tara"]), 2))
        vast_str = str(round(float(fila["Suma_Vastago"]), 2))
        descuentos.append({
            "Fecha": fecha_str,
            "Hora": ahora.strftime("%H:%M"),
            "Semana": semana_num,
            "Lote": lote_norm,
            "Parcelero": str(round(float(fila["Suma_Bruto"]), 2)),
            "Color_Cinta": color_norm,
            "Racimos": -cant,
            "Estado": f"{tara_str}|{vast_str}"
        })
    return descuentos



def mostrar_reportes_embolse(df, prefijo, lote_qr="Todos"):
    solo_emb = df[df["Racimos"] > 0].copy() if not df.empty else pd.DataFrame()
    if solo_emb.empty:
        st.info("Aún no hay registros de embolse en el sistema.")
        return
    ahora = datetime.now()
    solo_emb["Fecha"] = solo_emb["Fecha"].astype(str).str.strip().str[:10]
    solo_emb["Fecha_Dt"] = pd.to_datetime(solo_emb["Fecha"], errors="coerce").dt.date
    solo_emb["Anio"] = solo_emb["Fecha"].str[:4]
    solo_emb["Semana"] = solo_emb["Semana"].astype(int)

    fechas_validas = solo_emb["Fecha_Dt"].dropna()
    fecha_min = fechas_validas.min() if not fechas_validas.empty else ahora.date()
    fecha_max = fechas_validas.max() if not fechas_validas.empty else ahora.date()

    r1, r2 = st.columns(2)
    f_desde = r1.date_input("Desde fecha:", value=fecha_min, min_value=fecha_min, max_value=fecha_max, key=f"{prefijo}_desde")
    f_hasta = r2.date_input("Hasta fecha:", value=fecha_max, min_value=fecha_min, max_value=fecha_max, key=f"{prefijo}_hasta")

    sem_act = ahora.isocalendar().week
    anio_act = ahora.year
    solo_emb["Edad_Num"] = solo_emb.apply(
        lambda r: max(0, ((anio_act - int(r["Anio"])) * 52 + (sem_act - int(r["Semana"]))) + 1), axis=1
    )
    solo_emb["Edad_Texto"] = solo_emb["Edad_Num"].astype(str) + " sem"

    f1, f2, f3 = st.columns(3)
    sel_anio = f1.selectbox("Año:", ["Todos"] + sorted(solo_emb["Anio"].unique().tolist(), reverse=True), key=f"{prefijo}_anio")
    semanas_disp = sorted(solo_emb["Semana"].unique().tolist(), reverse=True)
    sel_sem = f2.multiselect("Semanas Embolse (vacío = todas):", semanas_disp, key=f"{prefijo}_sem")
    edades_disp = [f"{e} sem" for e in sorted(solo_emb["Edad_Num"].unique().tolist(), reverse=True)]
    sel_edad = f3.multiselect("Edades (vacío = todas):", edades_disp, key=f"{prefijo}_edad")

    f3, f4, f5 = st.columns(3)
    lotes_op = ["Todos"] + sorted(solo_emb["Lote"].unique().tolist())
    idx_lote = lotes_op.index(lote_qr) if lote_qr in lotes_op else 0
    sel_lote = f3.selectbox("Lote:", lotes_op, index=idx_lote, key=f"{prefijo}_lote")
    sel_color = f4.selectbox("Color de Cinta:", ["Todos"] + sorted(solo_emb["Color_Cinta"].unique().tolist()), key=f"{prefijo}_color")
    sel_emp = f5.selectbox("Empleado:", ["Todos"] + sorted(solo_emb["Parcelero"].unique().tolist()), key=f"{prefijo}_emp")

    df_res = solo_emb[(solo_emb["Fecha_Dt"] >= f_desde) & (solo_emb["Fecha_Dt"] <= f_hasta)].copy()
    if sel_anio != "Todos":
        df_res = df_res[df_res["Anio"] == sel_anio]
    if sel_sem:
        df_res = df_res[df_res["Semana"].isin(sel_sem)]
    if sel_edad:
        df_res = df_res[df_res["Edad_Texto"].isin(sel_edad)]

    if sel_lote != "Todos":
        df_res = df_res[df_res["Lote"] == sel_lote]
    if sel_color != "Todos":
        df_res = df_res[df_res["Color_Cinta"] == sel_color]
    if sel_emp != "Todos":
        df_res = df_res[df_res["Parcelero"] == sel_emp]

    total_filtrado = int(df_res["Racimos"].sum())
    st.metric("Total General (Según Filtros)", f"{total_filtrado:,} racimos")

    def formatear_cintas_visual(texto_cintas):
        iconos = {
            "Amarilla": "🟡 Amarilla", "Morada": "🟣 Morada",
            "Roja": "🔴 Roja", "Cafe": "🟤 Cafe",
            "Negra": "⚫ Negra", "Verde": "🟢 Verde",
            "Azul": "🔵 Azul", "Blanca": "⚪ Blanca"
        }
        partes = [p.strip() for p in str(texto_cintas).split(",") if p.strip() != "-"]
        if not partes:
            return "-"
        return " | ".join([iconos.get(p, p) for p in partes])

    def pintar_cinta(val):
        texto = str(val)
        paleta = {
            "Amarilla": ("#FFD700", "#000000"),
            "Morada": ("#800080", "#FFFFFF"),
            "Roja": ("#D32F2F", "#FFFFFF"),
            "Cafe": ("#6D4C41", "#FFFFFF"),
            "Negra": ("#212121", "#FFFFFF"),
            "Verde": ("#2E7D32", "#FFFFFF"),
            "Azul": ("#1565C0", "#FFFFFF"),
            "Blanca": ("#F5F5F5", "#000000")
        }
        encontrados = [par for nom, par in paleta.items() if nom in texto]
        if len(encontrados) == 1:
            fondo, letra = encontrados.pop(0)
            return f"background-color: {fondo}; color: {letra}; font-weight: bold;"
        elif len(encontrados) > 1:
            return "background-color: #263238; color: #FFFFFF; font-weight: bold;"
        return ""


    num_semanas = max(1, int(df_res["Semana"].nunique())) if not df_res.empty else 1
    st.caption(f"Cálculo de Racimos/Ha promediado sobre **{num_semanas} semana(s)** activas en el filtro.")

    st.write("### 1. Rendimiento por Lote (Racimos / Ha / Semana)")
    res_lote_ha = pd.DataFrame({"Lote": LOTES})
    res_lote_ha["Hectareas"] = res_lote_ha["Lote"].map(HECTAREAS_LOTE).fillna(0.0)
    emb_lote = df_res.groupby("Lote").agg(
        Cintas=("Color_Cinta", lambda x: ", ".join(sorted(set(x)))),
        Racimos=("Racimos", "sum")
    ).reset_index()
    res_lote_ha = res_lote_ha.merge(emb_lote, on="Lote", how="left").fillna({"Cintas": "-", "Racimos": 0})
    res_lote_ha["Racimos"] = res_lote_ha["Racimos"].astype(int)
    res_lote_ha["Racimos_Por_Ha"] = res_lote_ha.apply(
        lambda r: round(r["Racimos"] / (r["Hectareas"] * num_semanas), 1) if r["Hectareas"] > 0 else 0.0, axis=1
    )
    res_lote_ha["Cintas"] = res_lote_ha["Cintas"].apply(formatear_cintas_visual)

    tot_ha = round(res_lote_ha["Hectareas"].sum(), 2)
    tot_rac_lote = int(res_lote_ha["Racimos"].sum())
    prom_ha_total = round(tot_rac_lote / (tot_ha * num_semanas), 1) if tot_ha > 0 else 0.0
    fila_tot_1 = pd.DataFrame([{"Lote": "TOTAL", "Hectareas": tot_ha, "Cintas": "-", "Racimos": tot_rac_lote, "Racimos_Por_Ha": prom_ha_total}])
    t1_final = pd.concat([res_lote_ha, fila_tot_1], ignore_index=True)
    filas_1 = t1_final.index < len(res_lote_ha)
    st.dataframe(
        t1_final.style.background_gradient(subset=(filas_1, ["Racimos_Por_Ha"]), cmap="coolwarm_r")
                      .map(pintar_cinta, subset=["Cintas"])
                      .format({"Hectareas": "{:.2f}", "Racimos_Por_Ha": "{:.1f}"}),
        use_container_width=True, hide_index=True
    )

    st.write("### 2. Ranking de Empleados (Cantidad Total y Promedio por Día)")
    if not df_res.empty:
        rank_emp = df_res.groupby("Parcelero").agg(
            Total_Racimos=("Racimos", "sum"),
            Dias_Trabajados=("Fecha", "nunique")
        ).reset_index()
        rank_emp["Promedio_Por_Dia"] = (rank_emp["Total_Racimos"] / rank_emp["Dias_Trabajados"]).round(1)
        rank_emp = rank_emp.sort_values(by="Total_Racimos", ascending=False).reset_index(drop=True)
        tot_rac_emp = int(rank_emp["Total_Racimos"].sum())
        tot_dias_emp = int(rank_emp["Dias_Trabajados"].sum())
        prom_emp_tot = round(tot_rac_emp / tot_dias_emp, 1) if tot_dias_emp > 0 else 0.0
        fila_tot_2 = pd.DataFrame([{"Parcelero": "TOTAL", "Total_Racimos": tot_rac_emp, "Dias_Trabajados": tot_dias_emp, "Promedio_Por_Dia": prom_emp_tot}])
        t2_final = pd.concat([rank_emp, fila_tot_2], ignore_index=True)
        filas_2 = t2_final.index < len(rank_emp)
        st.dataframe(
            t2_final.style.background_gradient(subset=(filas_2, ["Total_Racimos", "Promedio_Por_Dia"]), cmap="coolwarm_r")
                          .format({"Promedio_Por_Dia": "{:.1f}"}),
            use_container_width=True, hide_index=True
        )
        st.write("### 3. Matriz de Embolse por Empleado y Lote (Con Fecha en Cada Celda)")
    if not df_res.empty:
        piv_num = df_res.pivot_table(index="Parcelero", columns="Lote", values="Racimos", aggfunc="sum", fill_value=0)
        lotes_activos = [lt for lt in LOTES if lt in piv_num.columns]
        tot_por_emp = piv_num[lotes_activos].sum(axis=1).sort_values(ascending=False)
        orden_emps = tot_por_emp.index.tolist()

        df_det_celda = df_res.copy()
        df_det_celda["Dia_Corto"] = pd.to_datetime(df_det_celda["Fecha"], errors="coerce").dt.strftime("%d/%m").fillna(df_det_celda["Fecha"].str[5:])
        grp_celda = df_det_celda.groupby(["Parcelero", "Lote", "Dia_Corto"])["Racimos"].sum().reset_index()

        celdas_texto = {}
        for (emp_k, lt_k), sub_g in grp_celda.groupby(["Parcelero", "Lote"]):
            partes = [f"{int(r['Racimos'])} ({r['Dia_Corto']})" for _, r in sub_g.iterrows()]
            celdas_texto[(emp_k, lt_k)] = " + ".join(partes)

        filas_mat3 = []
        for emp_n in orden_emps:
            fila_d = {"Parcelero": emp_n}
            for lt_n in lotes_activos:
                fila_d[lt_n] = celdas_texto.get((emp_n, lt_n), "0")
            fila_d["TOTAL"] = int(tot_por_emp[emp_n])
            filas_mat3.append(fila_d)

        fila_tot_emp = {"Parcelero": "TOTAL"}
        for lt_n in lotes_activos:
            fila_tot_emp[lt_n] = int(piv_num[lt_n].sum())
        fila_tot_emp["TOTAL"] = int(tot_por_emp.sum())

        mat_emp_final = pd.concat([pd.DataFrame(filas_mat3), pd.DataFrame([fila_tot_emp])], ignore_index=True)
        filas_me = mat_emp_final.index < len(filas_mat3)
        st.dataframe(
            mat_emp_final.style.background_gradient(subset=(filas_me, ["TOTAL"]), cmap="coolwarm_r"),
            use_container_width=True, hide_index=True
        )


def mostrar_saldos_y_proyeccion(df, prefijo, es_admin=False):

    if df.empty:
        st.info("Aún no hay movimientos registrados en el sistema.")
        return

    ahora = datetime.now()
    sem_hoy = ahora.isocalendar().week
    anio_hoy = ahora.year

    df_mat = df.copy()
    df_mat["Fecha"] = df_mat["Fecha"].astype(str).str.strip().str[:10]
    df_mat["Anio"] = df_mat["Fecha"].str[:4]
    df_mat["Semana"] = df_mat["Semana"].astype(int)


    ent_m = df_mat[df_mat["Racimos"] > 0].groupby(["Lote", "Color_Cinta", "Anio", "Semana"])["Racimos"].sum().reset_index()

    ent_m = ent_m.sort_values(by=["Lote", "Color_Cinta", "Anio", "Semana"])
    sal_m = df_mat[df_mat["Racimos"] < 0].groupby(["Lote", "Color_Cinta"])["Racimos"].sum().abs().to_dict()

    ICONOS_MATA = {
        "Amarilla": "🟡 Amarilla", "Morada": "🟣 Morada",
        "Roja": "🔴 Roja", "Cafe": "🟤 Cafe",
        "Negra": "⚫ Negra", "Verde": "🟢 Verde",
        "Azul": "🔵 Azul", "Blanca": "⚪ Blanca"
    }

    reg_fifo = []
    for _, r_m in ent_m.iterrows():
        lt, cl, an_s, sm, emb_v = r_m["Lote"], r_m["Color_Cinta"], str(r_m["Anio"]), int(r_m["Semana"]), int(r_m["Racimos"])
        desc_v = min(emb_v, sal_m.get((lt, cl), 0))
        sal_m[(lt, cl)] = sal_m.get((lt, cl), 0) - desc_v
        sld_v = emb_v - desc_v
        try:
            y_v = int(an_s)
        except Exception:
            y_v = anio_hoy
        ed_v = max(0, ((anio_hoy - y_v) * 52 + (sem_hoy - sm)) + 1)
        cl_vis = ICONOS_MATA.get(cl, cl)
        etiq = f"{cl_vis} ({ed_v} sem)"
        reg_fifo.append({
            "Lote": lt, "Color_Cinta": cl, "Anio": an_s, "Semana_Emb": sm,
            "Edad_Num": ed_v, "Edad_Txt": f"{ed_v} sem", "Etiqueta": etiq,
            "Orden_Ed": -ed_v, "Embolsados": emb_v, "Cortados": desc_v, "Saldo": sld_v
        })

    for (lt_s, cl_s), sob_v in sal_m.items():
        if sob_v > 0:
            reg_fifo.append({
                "Lote": lt_s, "Color_Cinta": cl_s, "Anio": "-", "Semana_Emb": 0,
                "Edad_Num": 0, "Edad_Txt": "Sin embolse previo", "Etiqueta": f"{cl_s} (Sin emb)",
                "Orden_Ed": 999, "Embolsados": 0, "Cortados": int(sob_v), "Saldo": -int(sob_v)
            })

    df_fifo_m = pd.DataFrame(reg_fifo)

    if not es_admin:
        st.subheader("1. Matriz de Saldo en Mata por Lote, Cinta y Edad")
        solo_pos_m = df_fifo_m[df_fifo_m["Saldo"] > 0].copy() if not df_fifo_m.empty else pd.DataFrame()
        if solo_pos_m.empty:
            st.info("No hay saldos positivos en mata actualmente.")
        else:
            edades_m_disp = [f"{e} sem" for e in sorted(solo_pos_m["Edad_Num"].unique().tolist(), reverse=True)]
            sel_edad_mata = st.multiselect("Filtrar Saldo en Mata por Edad (vacío = todas):", edades_m_disp, key=f"{prefijo}_edad_mata")
            if sel_edad_mata:
                solo_pos_m = solo_pos_m[solo_pos_m["Edad_Txt"].isin(sel_edad_mata)]

            if not solo_pos_m.empty:
                cols_ordenadas = solo_pos_m.sort_values(by=["Orden_Ed", "Etiqueta"])["Etiqueta"].unique().tolist()
                piv_saldo = solo_pos_m.pivot_table(index="Lote", columns="Etiqueta", values="Saldo", aggfunc="sum", fill_value=0)

                matriz_final = pd.DataFrame({"Lote": LOTES})
                for col_et in cols_ordenadas:
                    matriz_final[col_et] = matriz_final["Lote"].map(piv_saldo[col_et]).fillna(0).astype(int)
                matriz_final["Saldo_En_Mata"] = matriz_final[cols_ordenadas].sum(axis=1).astype(int)

                fila_tot_m = {"Lote": "TOTAL"}
                for col_num in cols_ordenadas + ["Saldo_En_Mata"]:
                    fila_tot_m[col_num] = int(matriz_final[col_num].sum())
                matriz_con_tot = pd.concat([matriz_final, pd.DataFrame([fila_tot_m])], ignore_index=True)
                st.dataframe(matriz_con_tot, use_container_width=True, hide_index=True)
            else:
                st.info("No hay saldo en mata para las edades seleccionadas.")

        st.subheader("2. Gráfica de Saldos en Mata por Lote y Color de Cinta")
        if not solo_pos_m.empty:
            import altair as alt
            escala_cintas_m = alt.Scale(
                domain=["Amarilla", "Morada", "Roja", "Cafe", "Negra", "Verde", "Azul", "Blanca"],
                range=["#FFD700", "#800080", "#D32F2F", "#6D4C41", "#212121", "#2E7D32", "#1565C0", "#E0E0E0"]
            )
            df_sg_plot = solo_pos_m.groupby(["Lote", "Color_Cinta"])["Saldo"].sum().reset_index()
            bar_s = alt.Chart(df_sg_plot).mark_bar().encode(
                x=alt.X("Lote:N", sort=LOTES, title="Lote"),
                y=alt.Y("Saldo:Q", title="Saldo en Mata (Racimos)"),
                color=alt.Color("Color_Cinta:N", scale=escala_cintas_m, title="Cinta"),
                tooltip=["Lote", "Color_Cinta", "Saldo"]
            )
            txt_s_seg = alt.Chart(df_sg_plot).mark_text(baseline="middle", fontWeight="bold", fontSize=10).encode(
                x=alt.X("Lote:N", sort=LOTES),
                y=alt.Y("Saldo:Q", stack="zero", bandPosition=0.5),
                detail="Color_Cinta:N",
                color=alt.condition(
                    alt.FieldOneOfPredicate(field="Color_Cinta", oneOf=["Amarilla", "Blanca"]),
                    alt.value("#000000"),
                    alt.value("#FFFFFF")
                ),
                text=alt.Text("Saldo:Q", format=",.0f")
            )
            txt_s_tot = alt.Chart(df_sg_plot).mark_text(dy=-7, fontWeight="bold", fontSize=11, color="#FFFFFF").encode(
                x=alt.X("Lote:N", sort=LOTES),
                y=alt.Y("sum(Saldo):Q"),
                text=alt.Text("sum(Saldo):Q", format=",.0f")
            )
            st.altair_chart((bar_s + txt_s_seg + txt_s_tot).properties(height=360), use_container_width=True)

    if es_admin:
        st.divider()
        st.subheader("1. Proyección de Cosecha y Cajas (Solo Administrador)")
        df_guardada = cargar_config_proyeccion() if es_admin else pd.DataFrame()
        ratio_def = float(df_guardada["Ratio"].iloc) if (not df_guardada.empty and "Ratio" in df_guardada.columns) else 1.15
        merma_def = int(df_guardada["Merma"].iloc) if (not df_guardada.empty and "Merma" in df_guardada.columns) else 5

        col_r1, col_r2 = st.columns(2)
        ratio = col_r1.number_input("Ratio (Cajas / Racimo):", value=ratio_def, min_value=0.50, max_value=2.50, step=0.05, key=f"{prefijo}_ratio")
        merma = col_r2.slider("Merma estimada (%):", 0, 20, merma_def, key=f"{prefijo}_merma")


        if not df_fifo_m.empty:
            solo_positivos = df_fifo_m[df_fifo_m["Saldo"] > 0]
            total_racimos = int(solo_positivos["Saldo"].sum())
            cajas_est = total_racimos * (1 - merma / 100.0) * ratio
            m1, m2 = st.columns(2)
            m1.metric("Saldo Real en Mata", f"{total_racimos:,} racimos")
            m2.metric("Cajas Proyectadas (20 kg)", f"{cajas_est:,.0f} cajas")

            def pintar_cinta_proy(val):
                texto = str(val)
                paleta = {
                    "Amarilla": ("#FFD700", "#000000"),
                    "Morada": ("#800080", "#FFFFFF"),
                    "Roja": ("#D32F2F", "#FFFFFF"),
                    "Cafe": ("#6D4C41", "#FFFFFF"),
                    "Negra": ("#212121", "#FFFFFF"),
                    "Verde": ("#2E7D32", "#FFFFFF"),
                    "Azul": ("#1565C0", "#FFFFFF"),
                    "Blanca": ("#F5F5F5", "#000000")
                }
                for nombre, (fondo, letra) in paleta.items():
                    if nombre in texto:
                        return f"background-color: {fondo}; color: {letra}; font-weight: bold;"
                return ""

            st.write("### Balance Consolidado por Color y Edad (Toda la Finca)")
            bal_edad = solo_positivos.groupby(["Color_Cinta", "Anio", "Semana_Emb", "Edad_Txt"]).agg(
                Embolsados=("Embolsados", "sum"), Cortados=("Cortados", "sum"), Saldo_En_Mata=("Saldo", "sum")
            ).reset_index().rename(columns={"Edad_Txt": "Edad"})
            bal_edad["Cajas_Est"] = (bal_edad["Saldo_En_Mata"] * (1 - merma / 100.0) * ratio).round(0).astype(int)
            tot_be = pd.DataFrame([{
                "Color_Cinta": "TOTAL", "Anio": "", "Semana_Emb": "", "Edad": "",
                "Embolsados": int(bal_edad["Embolsados"].sum()),
                "Cortados": int(bal_edad["Cortados"].sum()),
                "Saldo_En_Mata": int(bal_edad["Saldo_En_Mata"].sum()),
                "Cajas_Est": int(bal_edad["Cajas_Est"].sum())
            }])
            bal_edad_tot = pd.concat([bal_edad, tot_be], ignore_index=True)
            st.dataframe(bal_edad_tot.style.map(pintar_cinta_proy, subset=["Color_Cinta"]), use_container_width=True, hide_index=True)
            st.divider()
            st.write("### 📅 Simulador Completo de Cosecha (12 Semanas - Calendario ISO Real)")
            st.caption("Edita los porcentajes de corte directamente en la tabla. Cada cinta envejece y pasa su saldo remanente (detallado por color y edad) a la semana siguiente.")

            if solo_positivos.empty:
                st.info("No hay saldos positivos en mata para simular cosechas futuras.")
            else:
                inv_sim = solo_positivos.groupby(["Color_Cinta", "Anio", "Semana_Emb", "Edad_Num"])["Saldo"].sum().reset_index()
                inv_sim["Saldo_Restante"] = inv_sim["Saldo"].astype(float)

                mapa_guardado = {}
                if not df_guardada.empty and "Semana_Proy" in df_guardada.columns:
                    for _, rg in df_guardada.iterrows():
                        mapa_guardado[str(rg["Semana_Proy"])] = {
                            "p12": int(rg["P12"]),
                            "p11": int(rg["P11"]),
                            "p10": int(rg["P10"]),
                            "p9": int(rg["P9"])
                        }

                filas_cfg_default = []
                for offset in range(13):
                    fecha_fut = ahora + timedelta(weeks=offset)
                    num_sem_fut = fecha_fut.isocalendar().week
                    etiqueta_sem = f"Sem {num_sem_fut} (Actual)" if offset == 0 else f"Sem {num_sem_fut} (+{offset} sem)"
                    prev = mapa_guardado.get(etiqueta_sem, {"p12": 100, "p11": 50, "p10": 30, "p9": 10})
                    filas_cfg_default.append({
                        "Orden": offset,
                        "Semana_Proy": etiqueta_sem,
                        "% 12+ sem": prev["p12"],
                        "% 11 sem": prev["p11"],
                        "% 10 sem": prev["p10"],
                        "% 9 sem": prev["p9"]
                    })

                df_cfg_init = pd.DataFrame(filas_cfg_default)
                df_cfg_edit = st.data_editor(
                    df_cfg_init,
                    column_config={
                        "Orden": None,
                        "Semana_Proy": st.column_config.TextColumn("Semana de Cosecha", disabled=True),
                        "% 12+ sem": st.column_config.NumberColumn("% 12+ sem", min_value=0, max_value=100, step=5, format="%d%%"),
                        "% 11 sem": st.column_config.NumberColumn("% 11 sem", min_value=0, max_value=100, step=5, format="%d%%"),
                        "% 10 sem": st.column_config.NumberColumn("% 10 sem", min_value=0, max_value=100, step=5, format="%d%%"),
                        "% 9 sem": st.column_config.NumberColumn("% 9 sem", min_value=0, max_value=100, step=5, format="%d%%"),
                    },
                    use_container_width=True,
                    hide_index=True,
                    key=f"{prefijo}_editor_pct_12sem"
                )

                b_g1, b_g2 = st.columns([2, 1])
                if b_g1.button("💾 Guardar Proyección para Pedido de Cajas", type="primary", use_container_width=True, key=f"{prefijo}_btn_save_proy"):
                    try:
                        guardar_config_proyeccion(df_cfg_edit, ratio, merma)
                        st.success("Proyección semanal, Ratio y Merma guardados en Google Sheets.")
                        time.sleep(1.2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar proyección: {repr(e)}")
                if b_g2.button("🔄 Restaurar Base (100/50/30/10)", use_container_width=True, key=f"{prefijo}_btn_reset_proy"):
                    try:
                        df_base_rst = pd.DataFrame([
                            {"Orden": i, "Semana_Proy": r["Semana_Proy"], "% 12+ sem": 100, "% 11 sem": 50, "% 10 sem": 30, "% 9 sem": 10}
                            for i, r in df_cfg_init.iterrows()
                        ])
                        guardar_config_proyeccion(df_base_rst, 1.15, 5)
                        st.info("Valores base restaurados.")
                        time.sleep(1.2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al restaurar: {repr(e)}")

                ICONOS_SIM = {
                    "Amarilla": "🟡", "Morada": "🟣", "Roja": "🔴", "Cafe": "🟤",
                    "Negra": "⚫", "Verde": "🟢", "Azul": "🔵", "Blanca": "⚪"
                }

                resumen_semanal = []
                filas_graf_ps = []

                for _, cfg_row in df_cfg_edit.iterrows():
                    off = int(cfg_row["Orden"])
                    et_sem = str(cfg_row["Semana_Proy"])
                    p12 = float(cfg_row["% 12+ sem"]) / 100.0
                    p11 = float(cfg_row["% 11 sem"]) / 100.0
                    p10 = float(cfg_row["% 10 sem"]) / 100.0
                    p9 = float(cfg_row["% 9 sem"]) / 100.0

                    detalles_sem = []
                    rac_corte_sem = 0.0

                    for idx_r, row_s in inv_sim.iterrows():
                        rem = row_s["Saldo_Restante"]
                        if rem <= 0:
                            continue
                        edad_en_esa_sem = int(row_s["Edad_Num"]) + off
                        if edad_en_esa_sem >= 12:
                            pct_corte = p12
                        elif edad_en_esa_sem == 11:
                            pct_corte = p11
                        elif edad_en_esa_sem == 10:
                            pct_corte = p10
                        elif edad_en_esa_sem == 9:
                            pct_corte = p9
                        else:
                            pct_corte = 0.0

                        rac_cortar = rem * pct_corte
                        inv_sim.at[idx_r, "Saldo_Restante"] = rem - rac_cortar

                        if rac_cortar >= 1:
                            rac_int = int(round(rac_cortar))
                            rac_corte_sem += rac_int
                            ico = ICONOS_SIM.get(row_s["Color_Cinta"], "")
                            detalles_sem.append((edad_en_esa_sem, f"{ico} {row_s['Color_Cinta']} ({edad_en_esa_sem} sem): {rac_int:,}"))
                            filas_graf_ps.append({
                                "Orden": off,
                                "Semana_Proy": et_sem,
                                "Color_Cinta": row_s["Color_Cinta"],
                                "Cajas_Est": round(rac_int * (1 - merma / 100.0) * ratio, 0)
                            })

                    detalles_sem.sort(key=lambda x: -x[0])
                    texto_detalle = "  |  ".join([d[1] for d in detalles_sem]) if detalles_sem else "Sin corte programado"

                    detalles_saldo = []
                    for _, row_rem in inv_sim.iterrows():
                        rem_v = int(round(row_rem["Saldo_Restante"]))
                        if rem_v > 0:
                            ed_rem = int(row_rem["Edad_Num"]) + off
                            ico_r = ICONOS_SIM.get(row_rem["Color_Cinta"], "")
                            detalles_saldo.append((ed_rem, f"{ico_r} {row_rem['Color_Cinta']} ({ed_rem} sem): {rem_v:,}"))

                    detalles_saldo.sort(key=lambda x: -x[0])
                    texto_saldo_pasa = "  |  ".join([d[1] for d in detalles_saldo]) if detalles_saldo else "0 (Todo cosechado)"


                    rac_tot_int = int(round(rac_corte_sem))
                    cajas_tot_int = int(round(rac_tot_int * (1 - merma / 100.0) * ratio))
                    saldo_pasa = int(round(inv_sim["Saldo_Restante"].sum()))

                    resumen_semanal.append({
                        "Semana_Cosecha": et_sem,
                        "Cintas_A_Cortar": texto_detalle,
                        "Racimos_Corte": rac_tot_int,
                        "Saldo_Que_Pasa": saldo_pasa,
                        "Detalle_Saldo_Que_Pasa": texto_saldo_pasa,
                        "Cajas_Proyectadas": cajas_tot_int
                    })

                df_res_semanal = pd.DataFrame(resumen_semanal)
                fila_tot_ps = pd.DataFrame([{
                    "Semana_Cosecha": "TOTAL CICLO (12 SEM)",
                    "Cintas_A_Cortar": "-",
                    "Racimos_Corte": int(df_res_semanal["Racimos_Corte"].sum()),
                    "Saldo_Que_Pasa": int(df_res_semanal["Saldo_Que_Pasa"].iloc[-1]),
                    "Detalle_Saldo_Que_Pasa": df_res_semanal["Detalle_Saldo_Que_Pasa"].iloc[-1],
                    "Cajas_Proyectadas": int(df_res_semanal["Cajas_Proyectadas"].sum())
                }])
                tabla_ps_final = pd.concat([df_res_semanal, fila_tot_ps], ignore_index=True)
                filas_ps_idx = tabla_ps_final.index < len(df_res_semanal)

                st.write("#### Plan Semanal de Embarques (Cintas a Cortar, Saldo por Color y Cajas)")
                st.dataframe(
                    tabla_ps_final.style.background_gradient(subset=(filas_ps_idx, ["Cajas_Proyectadas"]), cmap="coolwarm_r"),
                    use_container_width=True, hide_index=True
                )

                if filas_graf_ps:
                    import altair as alt
                    st.write("#### Gráfica de Cajas Proyectadas por Semana y Color de Cinta")
                    num_sems_ver = st.slider(
                        "Cantidad de semanas futuras a mostrar en la gráfica:",
                        min_value=1, max_value=12, value=6, key=f"{prefijo}_slider_sems_graf"
                    )
                    escala_ps = alt.Scale(
                        domain=["Amarilla", "Morada", "Roja", "Cafe", "Negra", "Verde", "Azul", "Blanca"],
                        range=["#FFD700", "#9C27B0", "#E53935", "#8D6E63", "#424242", "#43A047", "#1E88E5", "#F5F5F5"]
                    )
                    df_gp = pd.DataFrame(filas_graf_ps)
                    df_gp = df_gp[df_gp["Orden"] < num_sems_ver].groupby(["Orden", "Semana_Proy", "Color_Cinta"])["Cajas_Est"].sum().reset_index()
                    orden_sems_lbl = df_cfg_edit["Semana_Proy"].iloc[:num_sems_ver].tolist()

                    bar_ps = alt.Chart(df_gp).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                        x=alt.X("Semana_Proy:N", sort=orden_sems_lbl, title="Semana de Cosecha", axis=alt.Axis(labelAngle=-20)),
                        y=alt.Y("Cajas_Est:Q", title="Cajas Proyectadas (20 kg)"),
                        color=alt.Color("Color_Cinta:N", scale=escala_ps, title="Cinta"),
                        tooltip=["Semana_Proy", "Color_Cinta", alt.Tooltip("Cajas_Est:Q", format=",.0f")]
                    )
                    txt_ps_seg = alt.Chart(df_gp).mark_text(baseline="middle", fontWeight="bold", fontSize=11).encode(
                        x=alt.X("Semana_Proy:N", sort=orden_sems_lbl),
                        y=alt.Y("Cajas_Est:Q", stack="zero", bandPosition=0.5),
                        detail="Color_Cinta:N",
                        color=alt.condition(
                            alt.FieldOneOfPredicate(field="Color_Cinta", oneOf=["Amarilla", "Blanca"]),
                            alt.value("#000000"),
                            alt.value("#FFFFFF")
                        ),
                        text=alt.Text("Cajas_Est:Q", format=",.0f")
                    )
                    txt_ps_tot = alt.Chart(df_gp).mark_text(dy=-8, fontWeight="bold", fontSize=12, color="#FFFFFF").encode(
                        x=alt.X("Semana_Proy:N", sort=orden_sems_lbl),
                        y=alt.Y("sum(Cajas_Est):Q"),
                        text=alt.Text("sum(Cajas_Est):Q", format=",.0f")
                    )
                    graf_ps_final = (bar_ps + txt_ps_seg + txt_ps_tot).properties(
                        height=390, background="#1E2530", padding={"left": 12, "top": 18, "right": 12, "bottom": 12}
                    ).configure_axis(
                        labelColor="#E2E8F0", titleColor="#FFFFFF", gridColor="#334155", domainColor="#475569"
                    ).configure_legend(
                        labelColor="#E2E8F0", titleColor="#FFFFFF"
                    ).configure_view(strokeWidth=0)
                    st.altair_chart(graf_ps_final, use_container_width=True)


st.title("BANANERA LA LOLA S.A")

if len(st.session_state.cola_offline) > 0:
    st.warning(f"Tienes {len(st.session_state.cola_offline)} registro(s) guardados en el celular.")
    if st.button("Sincronizar ahora con Google Sheets", type="primary"):
        try:
            agregar_filas(st.session_state.cola_offline)
            st.session_state.cola_offline = []
            st.success("Registros sincronizados correctamente.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al sincronizar: {repr(e)}")

rol = st.radio("Selecciona perfil:", ["Parcelero (Embolse)", "Consulta de Embolse", "Administrador"], horizontal=True)

if rol == "Parcelero (Embolse)":
    st.subheader("Registro de Fruta Embolsada")
    lote_detectado = "Lote 01"
    if st.toggle("Activar cámara para escanear QR", key="qr_parcelero"):
        foto_qr = st.camera_input("Apunta al QR del Lote")
        if foto_qr:
            img_bgr = cv2.cvtColor(np.array(Image.open(foto_qr)), cv2.COLOR_RGB2BGR)
            dato_qr, _, _ = cv2.QRCodeDetector().detectAndDecode(img_bgr)
            if dato_qr in LOTES:
                lote_detectado = dato_qr
                st.success(f"Lote detectado: {lote_detectado}")
    if "form_id" not in st.session_state:
        st.session_state.form_id = 0
    fid = st.session_state.form_id

    opciones_lote = ["Selecciona Lote..."] + LOTES
    idx_lote_ini = opciones_lote.index(lote_detectado) if lote_detectado in opciones_lote else 0
    lote_sel = st.selectbox("Lote:", opciones_lote, index=idx_lote_ini, key=f"reg_lote_{fid}")
    opciones_parc = ["Selecciona Parcelero..."] + PARCELEROS_BASE
    sel_p = st.selectbox("Parcelero / Responsable:", opciones_parc, key=f"reg_parc_{fid}")
    if sel_p == "Otro (Escribir nombre)":
        parcelero = st.text_input("Nombre del trabajador:", key=f"reg_otro_{fid}").strip()
    else:
        parcelero = sel_p
    st.write("Toca el color de la cinta:")
    VISUAL_CINTAS = {
        "🟡 Amarilla": "Amarilla", "🟣 Morada": "Morada",
        "🔴 Roja": "Roja", "🟤 Cafe": "Cafe",
        "⚫ Negra": "Negra", "🟢 Verde": "Verde",
        "🔵 Azul": "Azul", "⚪ Blanca": "Blanca"
    }
    if "cinta_elegida" not in st.session_state:
        st.session_state.cinta_elegida = "Amarilla"
    cols_cinta = st.columns(4)
    for idx, (etiqueta, nombre_real) in enumerate(VISUAL_CINTAS.items()):
        with cols_cinta[idx % 4]:
            if st.button(etiqueta, key=f"cinta_{nombre_real}_{fid}", use_container_width=True):
                st.session_state.cinta_elegida = nombre_real
        cinta = st.session_state.cinta_elegida
    ESTILOS_BANNER = {
        "Amarilla": ("#FFD700", "#000000", "🟡"),
        "Morada": ("#800080", "#FFFFFF", "🟣"),
        "Roja": ("#D32F2F", "#FFFFFF", "🔴"),
        "Cafe": ("#6D4C41", "#FFFFFF", "🟤"),
        "Negra": ("#212121", "#FFFFFF", "⚫"),
        "Verde": ("#2E7D32", "#FFFFFF", "🟢"),
        "Azul": ("#1565C0", "#FFFFFF", "🔵"),
        "Blanca": ("#F5F5F5", "#000000", "⚪")
    }
    bg_c, txt_c, ico_c = ESTILOS_BANNER.get(cinta, ("#E0E0E0", "#000000", "🏷️"))
    st.markdown(
        f'<div style="background-color:{bg_c}; color:{txt_c}; padding:14px; border-radius:10px; '
        f'text-align:center; font-size:20px; font-weight:bold; border:2px solid #999; margin:10px 0;">'
        f'{ico_c} CINTA SELECCIONADA: {cinta.upper()}</div>',
        unsafe_allow_html=True
    )

    col_fecha, col_cant, col_edad = st.columns(3)
    fecha_embolse = col_fecha.date_input("Fecha del embolse:", value=datetime.now(), key=f"reg_fecha_{fid}")
    racimos = col_cant.number_input("Cantidad de racimos:", min_value=0, max_value=1000, value=0, key=f"reg_cant_{fid}")
    edad_reg = col_edad.number_input("Edad al embolsar (sem):", min_value=0, max_value=15, value=1, key=f"reg_edad_{fid}")
    if st.button("Guardar Embolse", type="primary", key=f"btn_save_emb_{fid}"):
        if lote_sel == "Selecciona Lote..." or parcelero in ["Selecciona Parcelero...", ""] or racimos <= 0:
            st.warning("⚠️ Selecciona el Lote, el Parcelero y escribe una cantidad mayor a 0.")
        else:
            ahora = datetime.now()
            sem_embolse = fecha_embolse.isocalendar().week
            sem_real = sem_embolse - (int(edad_reg) - 1)
            if sem_real <= 0:
                sem_real += 52
            elif sem_real > 52:
                sem_real -= 52
            registro = {
                "Fecha": fecha_embolse.strftime("%Y-%m-%d"),
                "Hora": ahora.strftime("%H:%M"),
                "Semana": sem_real,
                "Lote": lote_sel,
                "Parcelero": parcelero,
                "Color_Cinta": cinta,
                "Racimos": int(racimos),
                "Estado": "En campo"
            }
            try:
                agregar_filas([registro])
                st.success(f"Guardados {racimos} racimos ({cinta}) en {lote_sel}.")
                time.sleep(1.5)
                st.session_state.form_id += 1
                st.rerun()
            except Exception as e:
                st.error(f"Error técnico: {repr(e)}")




elif rol == "Consulta de Embolse":
    st.subheader("Consulta de Embolse (Puyas y Supervisores)")
    lote_qr = "Todos"
    if st.toggle("Activar cámara para escanear QR del Lote", key="qr_consulta"):
        foto_qr_p = st.camera_input("Apunta al QR del Lote")
        if foto_qr_p:
            img_bgr = cv2.cvtColor(np.array(Image.open(foto_qr_p)), cv2.COLOR_RGB2BGR)
            dato_qr, _, _ = cv2.QRCodeDetector().detectAndDecode(img_bgr)
            if dato_qr in LOTES:
                lote_qr = dato_qr
                st.success(f"Lote escaneado: {lote_qr}")
    df = cargar_datos()
    t_cons1, t_cons2 = st.tabs(["🌱 Reportes de Embolse", "📦 Saldos De Racimos"])
    with t_cons1:
        mostrar_reportes_embolse(df, prefijo="cons", lote_qr=lote_qr)
    with t_cons2:
        mostrar_saldos_y_proyeccion(df, prefijo="cons_proy")


elif rol == "Administrador":
    clave = st.text_input("Clave de Administrador:", type="password")
    if clave != CLAVE_ADMIN:
        if clave != "":
            st.error("Clave incorrecta.")
        st.stop()
    tab_proy, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Proyección de Cosecha", "🔪 Historial de Corte",
        "📥 Subir CSV Tableta", "✏️ Corregir / Borrar", "📊 Gráficos"
    
    ])
    df = cargar_datos()
    with tab_proy:
        mostrar_saldos_y_proyeccion(df, prefijo="adm_proy", es_admin=True)

    with tab2:

    


        st.subheader("Buscador y Matriz de Corte (Promedios de Peso)")
        solo_cortes = df[df["Racimos"] < 0].copy() if not df.empty else pd.DataFrame()
        if solo_cortes.empty:
            st.info("Aún no hay cortes registrados desde la tableta.")
        else:
            ahora_c = datetime.now()
            sem_act_c = ahora_c.isocalendar().week
            anio_act_c = ahora_c.year

            solo_cortes["Racimos_Cortados"] = solo_cortes["Racimos"].abs()
            solo_cortes["Fecha"] = solo_cortes["Fecha"].astype(str).str.strip().str[:10]
            solo_cortes["Fecha_Dt"] = pd.to_datetime(solo_cortes["Fecha"], errors="coerce").dt.date
            solo_cortes["Anio"] = solo_cortes["Fecha"].str[:4]
            solo_cortes["Semana"] = solo_cortes["Semana"].astype(int)

            sem_emb_ref = {}
            if not df.empty:
                ent_ref = df[df["Racimos"] > 0].groupby("Color_Cinta")["Semana"].min().to_dict()
                for c_k, sm_v in ent_ref.items():
                    sem_emb_ref[c_k] = int(sm_v)

            def obtener_sem_emb(fila_c):
                cl = fila_c["Color_Cinta"]
                if cl in sem_emb_ref:
                    return sem_emb_ref[cl]
                return max(1, int(fila_c["Semana"]) - 10)

            solo_cortes["Sem_Embolse"] = solo_cortes.apply(obtener_sem_emb, axis=1)
            solo_cortes["Edad_Num"] = solo_cortes.apply(
                lambda r: max(0, (int(r["Semana"]) - int(r["Sem_Embolse"])) + 1), axis=1
            )
            solo_cortes["Edad_Texto"] = solo_cortes["Edad_Num"].astype(str) + " sem"

            fechas_c_val = solo_cortes["Fecha_Dt"].dropna()
            f_min_c = fechas_c_val.min() if not fechas_c_val.empty else ahora_c.date()
            f_max_c = fechas_c_val.max() if not fechas_c_val.empty else ahora_c.date()

            rc1, rc2 = st.columns(2)
            c_desde = rc1.date_input("Desde fecha corte:", value=f_min_c, min_value=f_min_c, max_value=f_max_c, key="corte_desde")
            c_hasta = rc2.date_input("Hasta fecha corte:", value=f_max_c, min_value=f_min_c, max_value=f_max_c, key="corte_hasta")

            f1, f2, f3 = st.columns(3)
            filtro_anio = f1.selectbox("Año:", ["Todos"] + sorted(solo_cortes["Anio"].unique().tolist(), reverse=True), key="corte_anio")
            semanas_c_disp = sorted(solo_cortes["Semana"].unique().tolist(), reverse=True)
            filtro_sem = f2.multiselect("Semanas de Corte (vacío = todas):", semanas_c_disp, key="corte_sem")
            semanas_e_disp = sorted(solo_cortes["Sem_Embolse"].unique().tolist(), reverse=True)
            filtro_sem_emb = f3.multiselect("Semanas de Embolse (vacío = todas):", semanas_e_disp, key="corte_sem_emb")

            f4, f5, f6 = st.columns(3)
            edades_disp = [f"{e} sem" for e in sorted(solo_cortes["Edad_Num"].unique().tolist(), reverse=True)]
            filtro_edad = f4.multiselect("Edades al Corte (vacío = todas):", edades_disp, key="corte_edad")
            filtro_lote = f5.selectbox("Lote:", ["Todos"] + sorted(solo_cortes["Lote"].unique().tolist()), key="corte_lote")
            filtro_color = f6.selectbox("Color:", ["Todos"] + sorted(solo_cortes["Color_Cinta"].unique().tolist()), key="corte_color")

            df_filtrado = solo_cortes[(solo_cortes["Fecha_Dt"] >= c_desde) & (solo_cortes["Fecha_Dt"] <= c_hasta)].copy()
            if filtro_anio != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Anio"] == filtro_anio]
            if filtro_sem:
                df_filtrado = df_filtrado[df_filtrado["Semana"].isin(filtro_sem)]
            if filtro_sem_emb:
                df_filtrado = df_filtrado[df_filtrado["Sem_Embolse"].isin(filtro_sem_emb)]
            if filtro_edad:
                df_filtrado = df_filtrado[df_filtrado["Edad_Texto"].isin(filtro_edad)]
            if filtro_lote != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Lote"] == filtro_lote]
            if filtro_color != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Color_Cinta"] == filtro_color]

            def extraer_tara(val):
                partes = str(val).split("|")
                try:
                    return float(partes[0])
                except Exception:
                    return 0.0

            def extraer_vastago(val):
                partes = str(val).split("|")
                if len(partes) > 1:
                    try:
                        return float(partes[1])
                    except Exception:
                        return 0.0
                return 0.0

            df_filtrado["Peso_Bruto_kg"] = pd.to_numeric(df_filtrado["Parcelero"], errors="coerce").fillna(0.0)
            df_filtrado["Peso_Garrucha_kg"] = df_filtrado["Estado"].apply(extraer_tara)
            df_filtrado["Peso_Vastago_kg"] = df_filtrado["Estado"].apply(extraer_vastago)
            df_filtrado["Peso_Neto_kg"] = (df_filtrado["Peso_Bruto_kg"] - df_filtrado["Peso_Garrucha_kg"] - df_filtrado["Peso_Vastago_kg"]).clip(lower=0.0)

            total_cortados = int(df_filtrado["Racimos_Cortados"].sum())
            tot_bruto = float(df_filtrado["Peso_Bruto_kg"].sum())
            tot_tara = float(df_filtrado["Peso_Garrucha_kg"].sum())
            tot_vastago = float(df_filtrado["Peso_Vastago_kg"].sum())
            tot_neto = float(df_filtrado["Peso_Neto_kg"].sum())

            prom_bruto_tot = round(tot_bruto / total_cortados, 2) if total_cortados > 0 else 0.0
            prom_tara_tot = round(tot_tara / total_cortados, 2) if total_cortados > 0 else 0.0
            prom_vastago_tot = round(tot_vastago / total_cortados, 2) if total_cortados > 0 else 0.0
            prom_neto_tot = round(tot_neto / total_cortados, 2) if total_cortados > 0 else 0.0

            m_c1, m_c2, m_c3, m_c4, m_c5 = st.columns(5)
            m_c1.metric("Racimos", f"{total_cortados:,}")
            m_c2.metric("Prom. Bruto", f"{prom_bruto_tot:.2f} kg")
            m_c3.metric("Prom. Garrucha", f"{prom_tara_tot:.2f} kg")
            m_c4.metric("Prom. Vástago", f"{prom_vastago_tot:.2f} kg")
            m_c5.metric("Prom. Neto", f"{prom_neto_tot:.2f} kg")

            st.write("### Matriz de Cosecha por Lote, Cinta (Edad) y Pesos Promedio")
            ICONOS_CINTA_COL = {
                "Amarilla": "🟡 Amarilla", "Morada": "🟣 Morada",
                "Roja": "🔴 Roja", "Cafe": "🟤 Cafe",
                "Negra": "⚫ Negra", "Verde": "🟢 Verde",
                "Azul": "🔵 Azul", "Blanca": "⚪ Blanca"
            }
            df_filtrado["Cinta_Visual"] = df_filtrado["Color_Cinta"].map(ICONOS_CINTA_COL).fillna(df_filtrado["Color_Cinta"])
            df_filtrado["Cinta_Edad"] = df_filtrado["Cinta_Visual"] + " (" + df_filtrado["Edad_Texto"] + ")"
            piv_corte = df_filtrado.pivot_table(index="Lote", columns="Cinta_Edad", values="Racimos_Cortados", aggfunc="sum", fill_value=0)
            res_pesos_lote = df_filtrado.groupby("Lote").agg(
                Total_Racimos=("Racimos_Cortados", "sum"),
                Suma_Bruto=("Peso_Bruto_kg", "sum"),
                Suma_Tara=("Peso_Garrucha_kg", "sum"),
                Suma_Vastago=("Peso_Vastago_kg", "sum"),
                Suma_Neto=("Peso_Neto_kg", "sum")
            )

            mat_corte = pd.DataFrame({"Lote": LOTES})
            for col_ce in piv_corte.columns:
                mat_corte[col_ce] = mat_corte["Lote"].map(piv_corte[col_ce]).fillna(0).astype(int)

            mat_corte["Total_Racimos"] = mat_corte["Lote"].map(res_pesos_lote["Total_Racimos"]).fillna(0).astype(int)
            s_bruto_l = mat_corte["Lote"].map(res_pesos_lote["Suma_Bruto"]).fillna(0.0)
            s_tara_l = mat_corte["Lote"].map(res_pesos_lote["Suma_Tara"]).fillna(0.0)
            s_vast_l = mat_corte["Lote"].map(res_pesos_lote["Suma_Vastago"]).fillna(0.0)
            s_neto_l = mat_corte["Lote"].map(res_pesos_lote["Suma_Neto"]).fillna(0.0)

            mat_corte["Prom_Bruto_kg"] = [round(b / r, 2) if r > 0 else 0.0 for b, r in zip(s_bruto_l, mat_corte["Total_Racimos"])]
            mat_corte["Prom_Garrucha_kg"] = [round(t / r, 2) if r > 0 else 0.0 for t, r in zip(s_tara_l, mat_corte["Total_Racimos"])]
            mat_corte["Prom_Vastago_kg"] = [round(v / r, 2) if r > 0 else 0.0 for v, r in zip(s_vast_l, mat_corte["Total_Racimos"])]
            mat_corte["Prom_Neto_kg"] = [round(n / r, 2) if r > 0 else 0.0 for n, r in zip(s_neto_l, mat_corte["Total_Racimos"])]

            fila_tot_mc = {"Lote": "TOTAL"}
            for col_c in piv_corte.columns:
                fila_tot_mc[col_c] = int(mat_corte[col_c].sum())
            fila_tot_mc["Total_Racimos"] = total_cortados
            fila_tot_mc["Prom_Bruto_kg"] = prom_bruto_tot
            fila_tot_mc["Prom_Garrucha_kg"] = prom_tara_tot
            fila_tot_mc["Prom_Vastago_kg"] = prom_vastago_tot
            fila_tot_mc["Prom_Neto_kg"] = prom_neto_tot

            mat_corte_final = pd.concat([mat_corte, pd.DataFrame([fila_tot_mc])], ignore_index=True)
            filas_mc = mat_corte_final.index < len(mat_corte)
            st.dataframe(
                mat_corte_final.style.background_gradient(subset=(filas_mc, ["Prom_Neto_kg"]), cmap="coolwarm_r")
                                     .format({
                                         "Prom_Bruto_kg": "{:.2f}",
                                         "Prom_Garrucha_kg": "{:.2f}",
                                         "Prom_Vastago_kg": "{:.2f}",
                                         "Prom_Neto_kg": "{:.2f}"
                                     }),
                use_container_width=True, hide_index=True
            )

            csv_descarga = mat_corte_final.to_csv(index=False).encode("utf-8")
            st.download_button("Descargar Matriz de Corte en Excel (CSV)", data=csv_descarga, file_name="matriz_cortes_promedios.csv", mime="text/csv")

    with tab3:
        st.subheader("Descontar Corte con CSV Directo de Tableta")
        st.write("Sube el archivo .csv de la tableta (cada fila cuenta como 1 racimo).")
        archivo_csv = st.file_uploader("Seleccionar archivo .csv de la tableta", type=["csv"])
        if archivo_csv is not None:
            try:
                df_tab = pd.read_csv(archivo_csv, sep=None, engine="python")
            except Exception:
                archivo_csv.seek(0)
                df_tab = pd.read_csv(archivo_csv)
            columnas_archivo = df_tab.columns.tolist()
            c1, c2, c3 = st.columns(3)
            col_lote = c1.selectbox("Columna de Lote:", columnas_archivo, key="csv_col_lote")
            col_color = c2.selectbox("Columna de Color:", columnas_archivo, key="csv_col_color")
            col_fecha = c3.selectbox("Columna de Fecha:", ["Usar fecha de hoy"] + columnas_archivo, key="csv_col_fecha")
            c4, c5, c6 = st.columns(3)
            col_bruto = c4.selectbox("Peso Bruto (Opcional):", ["Ninguna"] + columnas_archivo, key="csv_col_bruto")
            col_tara = c5.selectbox("Peso Garrucha/Tara (Opcional):", ["Ninguna"] + columnas_archivo, key="csv_col_tara")
            col_vastago = c6.selectbox("Peso Vástago (Opcional):", ["Ninguna"] + columnas_archivo, key="csv_col_vastago")


            if col_lote == col_color or (col_fecha != "Usar fecha de hoy" and col_fecha in [col_lote, col_color]):
                st.info("👆 Selecciona columnas diferentes para **Lote**, **Color** y **Fecha** para generar la vista previa.")
            else:
                descuentos = procesar_csv_tableta(df_tab, col_lote, col_color, col_fecha, col_bruto, col_tara, col_vastago)

                if descuentos:
                    st.write("### Vista Previa: Qué va a descontar y de qué Edad (FIFO)")
                    ahora_sim = datetime.now()
                    sem_act_sim = ahora_sim.isocalendar().week
                    anio_act_sim = ahora_sim.year

                    stock_fifo = {}
                    if not df.empty:
                        df_sim = df.copy()
                        df_sim["Fecha"] = df_sim["Fecha"].astype(str)
                        df_sim["Anio"] = df_sim["Fecha"].str[:4]
                        ent_sim = df_sim[df_sim["Racimos"] > 0].groupby(["Lote", "Color_Cinta", "Anio", "Semana"])["Racimos"].sum().reset_index()
                        ent_sim = ent_sim.sort_values(by=["Lote", "Color_Cinta", "Anio", "Semana"])
                        sal_sim = df_sim[df_sim["Racimos"] < 0].groupby(["Lote", "Color_Cinta"])["Racimos"].sum().abs().to_dict()

                        for _, r_ent in ent_sim.iterrows():
                            lt = r_ent["Lote"]
                            cl = r_ent["Color_Cinta"]
                            try:
                                yr = int(r_ent["Anio"])
                            except Exception:
                                yr = anio_act_sim
                            sm = int(r_ent["Semana"])
                            cant_e = int(r_ent["Racimos"])
                            ya_cort = min(cant_e, sal_sim.get((lt, cl), 0))
                            sal_sim[(lt, cl)] = sal_sim.get((lt, cl), 0) - ya_cort
                            disp = cant_e - ya_cort
                            if disp > 0:
                                ed_sim = max(0, ((anio_act_sim - yr) * 52 + (sem_act_sim - sm)) + 1)
                                stock_fifo.setdefault((lt, cl), []).append({"edad": ed_sim, "disp": disp})

                    filas_previa = []
                    for d in descuentos:
                        lt_d = d["Lote"]
                        cl_d = d["Color_Cinta"]
                        por_cortar = abs(int(d["Racimos"]))
                        bolsas = stock_fifo.get((lt_d, cl_d), [])
                        detalle_edades = []
                        restante = por_cortar
                        for b in bolsas:
                            if restante <= 0:
                                break
                            if b["disp"] > 0:
                                toma = min(b["disp"], restante)
                                b["disp"] -= toma
                                restante -= toma
                                detalle_edades.append(f"{b['edad']} sem ({toma} rac)")
                        if restante > 0:
                            detalle_edades.append(f"⚠️ Sin saldo previo ({restante} rac)")
                        filas_previa.append({
                            "Fecha_Corte": d["Fecha"],
                            "Lote": lt_d,
                            "Color_Cinta": cl_d,
                            "Racimos_A_Descontar": por_cortar,
                            "Edad_Que_Descuenta": " + ".join(detalle_edades)
                        })

                    df_previa = pd.DataFrame(filas_previa)
                    total_prev = int(df_previa["Racimos_A_Descontar"].sum())
                    fila_tot_prev = pd.DataFrame([{
                        "Fecha_Corte": "TOTAL", "Lote": "", "Color_Cinta": "",
                        "Racimos_A_Descontar": total_prev, "Edad_Que_Descuenta": "-"
                    }])
                    df_previa_final = pd.concat([df_previa, fila_tot_prev], ignore_index=True)
                    st.dataframe(df_previa_final, use_container_width=True, hide_index=True)

                    fechas_ya_cortadas = set()
                    if not df.empty:
                        cortes_existentes = df[df["Racimos"] < 0]
                        fechas_ya_cortadas = set(cortes_existentes["Fecha"].astype(str).str.strip().str[:10].unique())

                    fechas_csv = set(d["Fecha"] for d in descuentos)
                    repetidas = sorted(fechas_csv.intersection(fechas_ya_cortadas))
                    solo_nuevos = [d for d in descuentos if d["Fecha"] not in fechas_ya_cortadas]

                    if repetidas:
                        st.warning(f"⚠️ Atención: Los días **{', '.join(repetidas)}** ya tienen cortes guardados en el sistema.")
                        if solo_nuevos:
                            cant_nueva = sum(abs(d["Racimos"]) for d in solo_nuevos)
                            if st.button(f"📥 Guardar SOLO los días nuevos ({cant_nueva:,} racimos)", type="primary", key="btn_csv_nuevos"):
                                agregar_filas(solo_nuevos)
                                st.success("Se guardaron únicamente los días nuevos sin duplicar los anteriores.")
                                time.sleep(1.5)
                                st.rerun()
                        else:
                            st.info("Todos los días de este archivo ya fueron descontados anteriormente.")
                    else:
                        if st.button("✅ Confirmar y Descontar Inventario", type="primary", key="btn_confirmar_csv"):
                            try:
                                agregar_filas(descuentos)
                                st.success(f"Listo. Se descontaron {total_prev:,} racimos respetando las fechas del CSV.")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error técnico al descontar: {repr(e)}")
    with tab4:
        st.subheader("Corregir o Eliminar Registros (Solo Administrador)")
        if not df.empty:
            cortes_df = df[df["Racimos"] < 0].copy()
            if not cortes_df.empty:
                cortes_df["Fila_Excel"] = cortes_df.index + 2
                cortes_df["Fecha_Limpia"] = cortes_df["Fecha"].astype(str).str.strip().str[:10]
                fechas_corte_disp = sorted(cortes_df["Fecha_Limpia"].unique().tolist(), reverse=True)
                with st.expander("🗑️ Borrar cosecha completa de un día (Cargar CSV de nuevo)"):
                    dia_borrar = st.selectbox("Selecciona la fecha de corte a eliminar:", fechas_corte_disp, key="sel_borrar_dia_corte")
                    filas_a_borrar = sorted(cortes_df[cortes_df["Fecha_Limpia"] == dia_borrar]["Fila_Excel"].tolist(), reverse=True)
                    rac_dia_borrar = int(cortes_df[cortes_df["Fecha_Limpia"] == dia_borrar]["Racimos"].abs().sum())
                    st.write(f"Se eliminarán **{len(filas_a_borrar)} registros** ({rac_dia_borrar:,} racimos cortados) del día **{dia_borrar}**.")
                    if st.button(f"🚨 Eliminar toda la cosecha del {dia_borrar}", type="primary", key="btn_confirm_del_dia"):
                        try:
                            borrar_multiples_filas_gsheet(filas_a_borrar)
                            st.success(f"Cosecha del {dia_borrar} eliminada por completo en 1 segundo.")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar cosecha: {repr(e)}")

        if st.button("🔄 Recargar lista desde Google Sheets", key="btn_recargar_edit"):
            with st.spinner("Sincronizando con Google Sheets..."):
                time.sleep(1.5)
            st.rerun()
        if df.empty:
            st.warning("No se cargaron registros. Presiona el botón de recargar arriba.")
        else:
            df_edit = df.copy()
            df_edit["Fila_Excel"] = df_edit.index + 2
            df_edit["Tipo"] = df_edit["Racimos"].apply(lambda x: "Embolse (+)" if int(x) > 0 else "Corte (-)")
            c_f1, c_f2 = st.columns(2)
            f_lote_ed = c_f1.selectbox("Buscar por Lote:", ["Todos"] + sorted(df_edit["Lote"].astype(str).unique().tolist()), key="ed_filtro_lote")
            f_tipo_ed = c_f2.selectbox("Buscar por Tipo:", ["Todos", "Embolse (+)", "Corte (-)"], key="ed_filtro_tipo")
            df_filtrado_ed = df_edit.copy()
            if f_lote_ed != "Todos":
                df_filtrado_ed = df_filtrado_ed[df_filtrado_ed["Lote"] == f_lote_ed]
            if f_tipo_ed != "Todos":
                df_filtrado_ed = df_filtrado_ed[df_filtrado_ed["Tipo"] == f_tipo_ed]
            todos_ordenados = df_filtrado_ed.iloc[::-1]
            st.write(f"Mostrando **{len(todos_ordenados)}** registros encontrados:")
            st.dataframe(todos_ordenados[["Fila_Excel", "Fecha", "Semana", "Lote", "Parcelero", "Color_Cinta", "Racimos", "Estado"]], use_container_width=True, hide_index=True)
            if not todos_ordenados.empty:
                fila_sel = st.selectbox("Selecciona el número de Fila_Excel:", todos_ordenados["Fila_Excel"].tolist(), key="sel_fila_ed")
                datos_fila = df_edit[df_edit["Fila_Excel"] == fila_sel].iloc[int(0)]
                st.divider()
                st.write(f"Editando **Fila {fila_sel}** ({datos_fila['Parcelero']}):")
                parc_actual = str(datos_fila["Parcelero"])
                opciones_parc = PARCELEROS_BASE[:-1] + ["Otro / Manual"]
                idx_p = opciones_parc.index(parc_actual) if parc_actual in opciones_parc else len(opciones_parc) - 1
                sel_parc_ed = st.selectbox("Corregir Parcelero:", opciones_parc, index=idx_p, key=f"ed_parc_{fila_sel}")
                if sel_parc_ed == "Otro / Manual":
                    nuevo_parcelero = st.text_input("Nombre del trabajador:", value=parc_actual, key=f"ed_parc_txt_{fila_sel}").strip() or parc_actual
                else:
                    nuevo_parcelero = sel_parc_ed
                try:
                    fecha_obj = datetime.strptime(str(datos_fila["Fecha"]).strip()[:10], "%Y-%m-%d").date()
                except Exception:
                    fecha_obj = datetime.now().date()
                e1, e2 = st.columns(2)
                nueva_fecha = e1.date_input("Corregir Fecha:", value=fecha_obj, key=f"ed_fecha_{fila_sel}")
                idx_l = LOTES.index(datos_fila["Lote"]) if datos_fila["Lote"] in LOTES else 0
                nuevo_lote = e2.selectbox("Corregir Lote:", LOTES, index=idx_l, key=f"ed_lote_{fila_sel}")
                e3, e4 = st.columns(2)
                idx_c = COLORES_CINTA.index(datos_fila["Color_Cinta"]) if datos_fila["Color_Cinta"] in COLORES_CINTA else 0
                nuevo_color = e3.selectbox("Corregir Color:", COLORES_CINTA, index=idx_c, key=f"ed_color_{fila_sel}")
                valor_actual = int(float(datos_fila["Racimos"]))
                cant_real = abs(valor_actual) if abs(valor_actual) > 0 else 1
                nueva_cant_abs = e4.number_input("Corregir Cantidad:", min_value=1, max_value=10000, value=int(cant_real), key=f"ed_cant_{fila_sel}")
                nuevo_racimos = -int(nueva_cant_abs) if valor_actual < 0 else int(nueva_cant_abs)
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("💾 Guardar Corrección", type="primary", use_container_width=True, key=f"btn_save_{fila_sel}"):
                    try:
                        nueva_semana = nueva_fecha.isocalendar().week
                        fila_actualizada = [
                            nueva_fecha.strftime("%Y-%m-%d"), str(datos_fila["Hora"]), int(nueva_semana),
                            nuevo_lote, nuevo_parcelero, nuevo_color,
                            nuevo_racimos, str(datos_fila["Estado"])
                        ]
                        actualizar_fila_gsheet(int(fila_sel), fila_actualizada)
                        st.success(f"Fila {fila_sel} actualizada correctamente.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al actualizar: {repr(e)}")
                if col_btn2.button("🗑️ Eliminar Fila", use_container_width=True, key=f"btn_del_{fila_sel}"):
                    try:
                        borrar_fila_gsheet(int(fila_sel))
                        st.warning(f"Fila {fila_sel} eliminada permanentemente.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar: {repr(e)}")

        with tab5:
        st.subheader("Análisis Gráfico de Producción, Saldos y Pesos")
        if df.empty:
            st.info("Aún no hay datos suficientes para generar gráficas.")
        else:
            import altair as alt

            ahora_g = datetime.now()
            sem_act_g = ahora_g.isocalendar().week
            anio_act_g = ahora_g.year

            df_g = df.copy()
            df_g["Fecha"] = df_g["Fecha"].astype(str).str.strip().str[:10]
            df_g["Fecha_Dt"] = pd.to_datetime(df_g["Fecha"], errors="coerce").dt.date
            df_g["Anio"] = df_g["Fecha"].str[:4]
            df_g["Semana"] = df_g["Semana"].astype(int)

            def calc_ed_g(r):
                try:
                    y_g = int(r["Anio"])
                except Exception:
                    y_g = anio_act_g
                return max(0, ((anio_act_g - y_g) * 52 + (sem_act_g - int(r["Semana"]))) + 1)

            df_g["Edad_Num"] = df_g.apply(calc_ed_g, axis=1)
            df_g["Edad_Txt"] = df_g["Edad_Num"].astype(str) + " sem"

            escala_cintas = alt.Scale(
                domain=["Amarilla", "Morada", "Roja", "Cafe", "Negra", "Verde", "Azul", "Blanca"],
                range=["#FFD700", "#9C27B0", "#E53935", "#8D6E63", "#424242", "#43A047", "#1E88E5", "#F5F5F5"]
            )

            def aplicar_tema_tarjeta(chart_obj, alto=380):
                return chart_obj.properties(
                    height=alto, background="#1E2530", padding={"left": 12, "top": 18, "right": 12, "bottom": 12}
                ).configure_axis(
                    labelColor="#E2E8F0", titleColor="#FFFFFF", gridColor="#334155", domainColor="#475569", labelAngle=0
                ).configure_legend(
                    labelColor="#E2E8F0", titleColor="#FFFFFF"
                ).configure_view(strokeWidth=0)

            st.markdown("### 🔪 Sección 1: Gráfica de Peso Neto Cortado")
            cortes_base = df_g[df_g["Racimos"] < 0].copy()
            if cortes_base.empty:
                st.info("No hay registros de corte para graficar.")
            else:
                fc_valid = cortes_base["Fecha_Dt"].dropna()
                min_gc = fc_valid.min() if not fc_valid.empty else ahora_g.date()
                max_gc = fc_valid.max() if not fc_valid.empty else ahora_g.date()

                gc1, gc2, gc3, gc4 = st.columns(4)
                c_desde_g = gc1.date_input("Desde corte:", value=min_gc, min_value=min_gc, max_value=max_gc, key="g_c_desde")
                c_hasta_g = gc2.date_input("Hasta corte:", value=max_gc, min_value=min_gc, max_value=max_gc, key="g_c_hasta")
                c_lote_g = gc3.selectbox("Lote (Corte):", ["Todos"] + LOTES, key="g_c_lote")
                sems_c_g = sorted(cortes_base["Semana"].unique().tolist(), reverse=True)
                c_sems_g = gc4.multiselect("Semanas de Corte:", sems_c_g, key="g_c_sems")

                cortes_g = cortes_base[(cortes_base["Fecha_Dt"] >= c_desde_g) & (cortes_base["Fecha_Dt"] <= c_hasta_g)].copy()
                if c_lote_g != "Todos":
                    cortes_g = cortes_g[cortes_g["Lote"] == c_lote_g]
                if c_sems_g:
                    cortes_g = cortes_g[cortes_g["Semana"].isin(c_sems_g)]

                if not cortes_g.empty:
                    def ext_tara_g(val):
                        try:
                            return float(str(val).split("|"))
                        except Exception:
                            return 0.0

                    def ext_vast_g(val):
                        partes = str(val).split("|")
                        if len(partes) > 1:
                            try:
                                return float(partes)
                            except Exception:
                                return 0.0
                        return 0.0

                    cortes_g["Bruto"] = pd.to_numeric(cortes_g["Parcelero"], errors="coerce").fillna(0.0)
                    cortes_g["Tara"] = cortes_g["Estado"].apply(ext_tara_g)
                    cortes_g["Vastago"] = cortes_g["Estado"].apply(ext_vast_g)
                    cortes_g["Peso_Neto_kg"] = (cortes_g["Bruto"] - cortes_g["Tara"] - cortes_g["Vastago"]).clip(lower=0.0)

                    grp_peso = cortes_g.groupby(["Lote", "Color_Cinta"])["Peso_Neto_kg"].sum().reset_index()
                    grp_peso["Peso_Neto_kg"] = grp_peso["Peso_Neto_kg"].round(1)
                    bar_p = alt.Chart(grp_peso).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                        x=alt.X("Lote:N", sort=LOTES, title="Lote"),
                        y=alt.Y("Peso_Neto_kg:Q", title="Peso Neto (kg)"),
                        color=alt.Color("Color_Cinta:N", scale=escala_cintas, title="Cinta"),
                        tooltip=["Lote", "Color_Cinta", alt.Tooltip("Peso_Neto_kg:Q", format=",.1f")]
                    )
                    txt_p = alt.Chart(grp_peso).mark_text(dy=-8, fontWeight="bold", fontSize=11, color="#FFFFFF").encode(
                        x=alt.X("Lote:N", sort=LOTES),
                        y=alt.Y("sum(Peso_Neto_kg):Q"),
                        text=alt.Text("sum(Peso_Neto_kg):Q", format=",.0f")
                    )
                    st.altair_chart(aplicar_tema_tarjeta(bar_p + txt_p), use_container_width=True)

            st.divider()
            st.markdown("### 🌱 Sección 2: Gráficas de Embolse y Saldo en Mata")
            emb_base = df_g[df_g["Racimos"] > 0].copy()
            if emb_base.empty:
                st.info("No hay registros de embolse para graficar.")
            else:
                fe_valid = emb_base["Fecha_Dt"].dropna()
                min_ge = fe_valid.min() if not fe_valid.empty else ahora_g.date()
                max_ge = fe_valid.max() if not fe_valid.empty else ahora_g.date()

                ge1, ge2, ge3 = st.columns(3)
                e_desde_g = ge1.date_input("Desde embolse:", value=min_ge, min_value=min_ge, max_value=max_ge, key="g_e_desde")
                e_hasta_g = ge2.date_input("Hasta embolse:", value=max_ge, min_value=min_ge, max_value=max_ge, key="g_e_hasta")
                e_lote_g = ge3.selectbox("Lote (Embolse/Saldo):", ["Todos"] + LOTES, key="g_e_lote")

                ge4, ge5, ge6 = st.columns(3)
                parcs_emb = sorted(emb_base["Parcelero"].astype(str).unique().tolist())
                e_parc_g = ge4.selectbox("Parcelero:", ["Todos"] + parcs_emb, key="g_e_parc")
                sems_e_g = sorted(emb_base["Semana"].unique().tolist(), reverse=True)
                e_sems_g = ge5.multiselect("Semanas de Embolse:", sems_e_g, key="g_e_sems")
                eds_e_g = [f"{e} sem" for e in sorted(emb_base["Edad_Num"].unique().tolist(), reverse=True)]
                e_eds_g = ge6.multiselect("Edades de Cinta:", eds_e_g, key="g_e_eds")

                emb_g = emb_base[(emb_base["Fecha_Dt"] >= e_desde_g) & (emb_base["Fecha_Dt"] <= e_hasta_g)].copy()
                if e_lote_g != "Todos":
                    emb_g = emb_g[emb_g["Lote"] == e_lote_g]
                if e_parc_g != "Todos":
                    emb_g = emb_g[emb_g["Parcelero"] == e_parc_g]
                if e_sems_g:
                    emb_g = emb_g[emb_g["Semana"].isin(e_sems_g)]
                if e_eds_g:
                    emb_g = emb_g[emb_g["Edad_Txt"].isin(e_eds_g)]

                if not emb_g.empty:
                    st.write("#### 2. Racimos Embolsados por Lote y Color de Cinta")
                    grp_emb = emb_g.groupby(["Lote", "Color_Cinta"])["Racimos"].sum().reset_index()
                    bar_e = alt.Chart(grp_emb).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                        x=alt.X("Lote:N", sort=LOTES, title="Lote"),
                        y=alt.Y("Racimos:Q", title="Racimos Embolsados"),
                        color=alt.Color("Color_Cinta:N", scale=escala_cintas, title="Cinta"),
                        tooltip=["Lote", "Color_Cinta", "Racimos"]
                    )
                    txt_e_seg = alt.Chart(grp_emb).mark_text(baseline="middle", fontWeight="bold", fontSize=10).encode(
                        x=alt.X("Lote:N", sort=LOTES),
                        y=alt.Y("Racimos:Q", stack="zero", bandPosition=0.5),
                        detail="Color_Cinta:N",
                        color=alt.condition(
                            alt.FieldOneOfPredicate(field="Color_Cinta", oneOf=["Amarilla", "Blanca"]),
                            alt.value("#000000"),
                            alt.value("#FFFFFF")
                        ),
                        text=alt.Text("Racimos:Q", format=",.0f")
                    )
                    txt_e_tot = alt.Chart(grp_emb).mark_text(dy=-8, fontWeight="bold", fontSize=11, color="#FFFFFF").encode(
                        x=alt.X("Lote:N", sort=LOTES),
                        y=alt.Y("sum(Racimos):Q"),
                        text=alt.Text("sum(Racimos):Q", format=",.0f")
                    )
                    st.altair_chart(aplicar_tema_tarjeta(bar_e + txt_e_seg + txt_e_tot), use_container_width=True)

                st.write("#### 3. Saldos en Mata por Lote y Color de Cinta")
                df_saldo_g = df_g.copy()
                if e_lote_g != "Todos":
                    df_saldo_g = df_saldo_g[df_saldo_g["Lote"] == e_lote_g]

                ent_sg = df_saldo_g[df_saldo_g["Racimos"] > 0]
                if e_parc_g != "Todos":
                    ent_sg = ent_sg[ent_sg["Parcelero"] == e_parc_g]
                ent_sg = ent_sg.groupby(["Lote", "Color_Cinta", "Anio", "Semana", "Edad_Txt"])["Racimos"].sum().reset_index()
                ent_sg = ent_sg.sort_values(by=["Lote", "Color_Cinta", "Anio", "Semana"])
                sal_sg = df_saldo_g[df_saldo_g["Racimos"] < 0].groupby(["Lote", "Color_Cinta"])["Racimos"].sum().abs().to_dict()

                filas_sg = []
                for _, r_sg in ent_sg.iterrows():
                    lt_s, cl_s, ed_t, emb_s = r_sg["Lote"], r_sg["Color_Cinta"], r_sg["Edad_Txt"], int(r_sg["Racimos"])
                    desc_s = min(emb_s, sal_sg.get((lt_s, cl_s), 0))
                    sal_sg[(lt_s, cl_s)] = sal_sg.get((lt_s, cl_s), 0) - desc_s
                    sld_s = emb_s - desc_s
                    if sld_s > 0:
                        if not e_eds_g or ed_t in e_eds_g:
                            if not e_sems_g or int(r_sg["Semana"]) in e_sems_g:
                                filas_sg.append({"Lote": lt_s, "Color_Cinta": cl_s, "Saldo_En_Mata": sld_s})

                if filas_sg:
                    df_sg_plot = pd.DataFrame(filas_sg).groupby(["Lote", "Color_Cinta"])["Saldo_En_Mata"].sum().reset_index()
                    bar_s = alt.Chart(df_sg_plot).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                        x=alt.X("Lote:N", sort=LOTES, title="Lote"),
                        y=alt.Y("Saldo_En_Mata:Q", title="Saldo en Mata (Racimos)"),
                        color=alt.Color("Color_Cinta:N", scale=escala_cintas, title="Cinta"),
                        tooltip=["Lote", "Color_Cinta", "Saldo_En_Mata"]
                    )
                    txt_s_seg = alt.Chart(df_sg_plot).mark_text(baseline="middle", fontWeight="bold", fontSize=10).encode(
                        x=alt.X("Lote:N", sort=LOTES),
                        y=alt.Y("Saldo_En_Mata:Q", stack="zero", bandPosition=0.5),
                        detail="Color_Cinta:N",
                        color=alt.condition(
                            alt.FieldOneOfPredicate(field="Color_Cinta", oneOf=["Amarilla", "Blanca"]),
                            alt.value("#000000"),
                            alt.value("#FFFFFF")
                        ),
                        text=alt.Text("Saldo_En_Mata:Q", format=",.0f")
                    )
                    txt_s_tot = alt.Chart(df_sg_plot).mark_text(dy=-8, fontWeight="bold", fontSize=11, color="#FFFFFF").encode(
                        x=alt.X("Lote:N", sort=LOTES),
                        y=alt.Y("sum(Saldo_En_Mata):Q"),
                        text=alt.Text("sum(Saldo_En_Mata):Q", format=",.0f")
                    )
                    st.altair_chart(aplicar_tema_tarjeta(bar_s + txt_s_seg + txt_s_tot), use_container_width=True)
                else:
                    st.info("No hay saldos en mata disponibles para los filtros seleccionados.")
