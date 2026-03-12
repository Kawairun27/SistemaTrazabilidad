import streamlit as st
import os 
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from fpdf import FPDF
from PIL import Image

# --- CONFIGURACIÓN DE BASE DE DATOS ---
engine = create_engine('sqlite:///trazabilidad_v2.db')
Base = declarative_base()

class Pedido(Base):
    __tablename__ = 'pedidos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(DateTime, default=datetime.now)
    usuario_id = Column(Integer)
class Unidad(Base):
    __tablename__ = 'unidades'
    codigo_xz = Column(String, primary_key=True)
    modelo = Column(String)
    etapa = Column(String)
    pedido_id = Column(Integer)
    ultima_actualizacion = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# --- Función PDF Actualizada ---
def crear_pdf_cotizacion(codigo, producto, num_orden):
    pdf = FPDF()
    pdf.add_page()
    
    # Datos técnicos mapeados con extensiones corregidas
    INFO = {
        "Apex-15 Stealth": {"specs": "i7-13700H, RTX 4070, 16GB RAM", "tiempo": "5 días", "img": "images/Apex-15Stealth.webp.webp"},
        "Titan-18 Ultra": {"specs": "i9-14900HX, RTX 4090, 32GB RAM", "tiempo": "7 días", "img": "images/Titan18Ultra.webp.webp"},
        "Horizon-G Pro": {"specs": "Ryzen 9, RTX 4080, Liquid Cooling", "tiempo": "6 días", "img": "images/HorizonG-pro.jpg"},
        "Workstation-X": {"specs": "Xeon Gold, 64GB ECC, Quadro RTX", "tiempo": "8 días", "img": "images/WorkstationX.jpg"},
        "GPU-Vortex 90": {"specs": "24GB GDDR6X, Triple Fan, DLSS 3.5", "tiempo": "3 días", "img": "images/GpuVortex.webp.webp"},
        "RAM-Fury 64GB": {"specs": "DDR5 6000MHz, CL30, RGB", "tiempo": "2 días", "img": "images/RAM-Fury-64gb.jpg"}
    }

    # Encabezado Corporativo
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(40, 70, 120)
    pdf.cell(200, 15, txt="TECHARMOR RD - HOJA DE TRAZABILIDAD", ln=True, align='C')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(200, 10, txt=f"ORDEN DE PRODUCCIÓN: #{num_orden:03d} | ID: {codigo}", ln=True, align='C')
    pdf.ln(5)

    # Bloque de Información
    pdf.set_font("Arial", size=11)
    pdf.cell(100, 10, txt=f"Modelo: {producto}", ln=True)
    
    if producto in INFO:
        pdf.multi_cell(0, 10, txt=f"Especificaciones Técnicas: {INFO[producto]['specs']}")
        pdf.cell(100, 10, txt=f"Tiempo Estándar de Entrega: {INFO[producto]['tiempo']}", ln=True)
        pdf.ln(5)
        
        # --- LÓGICA PARA IMÁGENES WEBP ---
        ruta_img = INFO[producto]['img']
        if os.path.exists(ruta_img):
            if ruta_img.lower().endswith(".webp"):
                # Si es webp, lo convertimos a un formato temporal que FPDF acepte
                img_temp = Image.open(ruta_img).convert("RGB")
                img_temp_path = ruta_img.replace(".webp", "_temp.jpg")
                img_temp.save(img_temp_path, "JPEG")
                
                pdf.image(img_temp_path, x=55, y=pdf.get_y(), w=100)
                
                # Opcional: Borrar el temporal después de usarlo (puedes comentarlo si falla)
                os.remove(img_temp_path) 
            else:
                # Si ya es .jpg o .png, se inserta normal
                pdf.image(ruta_img, x=55, y=pdf.get_y(), w=100)
    
    # Pie de página Normativo
    pdf.set_y(-40)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, txt="Documento generado bajo estándares de Normalización ISO 9001:2015 - Grupo I", align='C', ln=True)
    pdf.cell(0, 10, txt="La manipulación de este equipo debe seguir los protocolos de Metrología establecidos.", align='C')

    nombre_archivo = f"HojaTecnica_{codigo}.pdf"
    pdf.output(nombre_archivo)
    return nombre_archivo

# --- INTERFAZ PRODUCCIÓN ---
st.set_page_config(page_title="Panel de Producción ISO", layout="wide")
st.title("🏭 Departamento de Producción (Trazabilidad)")

# --- SECCIÓN DE CONTADORES Y PRIORIDADES ---
st.subheader("📊 Indicadores de Prioridad (KPIs)")

# Obtenemos unidades que no han sido despachadas
pendientes = session.query(Unidad).filter(Unidad.etapa != "Despacho").all()
total_pendientes = len(pendientes)

col_met1, col_met2, col_met3 = st.columns(3)

with col_met1:
    st.metric("Órdenes en curso", total_pendientes)

# Análisis jerárquico de prioridad
unidades_con_fecha = []
for u in pendientes:
    # Buscamos la fecha del pedido original
    pedido = session.query(Pedido).filter(Pedido.id == u.pedido_id).first()
    if pedido:
        dias_transcurridos = (datetime.now() - pedido.fecha).days
        # Unidades con más de 3 días son "Prioridad Media", más de 5 es "CRÍTICO"
        prioridad = "Baja"
        if dias_transcurridos >= 5: prioridad = "🔥 CRÍTICO"
        elif dias_transcurridos >= 3: prioridad = "⚠️ MEDIA"
        
        unidades_con_fecha.append({
            "obj": u,
            "dias": dias_transcurridos,
            "prioridad": prioridad
        })

# Ordenar jerárquicamente: primero los que tienen más días transcurridos
unidades_con_fecha = sorted(unidades_con_fecha, key=lambda x: x['dias'], reverse=True)

with col_met2:
    criticos = [x for x in unidades_con_fecha if x['dias'] >= 5]
    st.metric("Órdenes Críticas (>5 días)", len(criticos), delta_color="inverse")

with col_met3:
    if unidades_con_fecha:
        mas_antigua = unidades_con_fecha[0]['obj'].codigo_xz
        st.write(f"🚩 **Atender primero:**")
        st.error(f"{mas_antigua} ({unidades_con_fecha[0]['dias']} días)")

st.divider()

# --- CUERPO PRINCIPAL ---
st.subheader("🛠️ Línea de Producción")

if not unidades_con_fecha:
    # Si no hay pendientes, mostramos las terminadas por si acaso
    st.info("No hay órdenes pendientes. ¡Buen trabajo!")
    unidades_para_mostrar = session.query(Unidad).order_by(Unidad.pedido_id.desc()).all()
else:
    # Mostramos las pendientes ordenadas por prioridad (la más vieja arriba)
    unidades_para_mostrar = [x['obj'] for x in unidades_con_fecha]

for u in unidades_para_mostrar:
    # Buscar info extra para el expander
    info_prio = next((item for item in unidades_con_fecha if item["obj"].codigo_xz == u.codigo_xz), None)
    label_prio = f" | PRIORIDAD: {info_prio['prioridad']}" if info_prio else " | ✅ COMPLETADO"
    
    with st.expander(f"📦 Orden #{u.pedido_id:03d} | Item: {u.codigo_xz}{label_prio}"):
        col_info, col_progreso = st.columns([1, 2])
        with col_info:
            st.write(f"**Modelo:** {u.modelo}")
            if info_prio:
                st.write(f"**Días en planta:** {info_prio['dias']}")
            st.write(f"**Última act.:** {u.ultima_actualizacion.strftime('%H:%M:%S')}")
        
        with col_progreso:
            nueva_etapa = st.select_slider(
                "Cambiar Etapa:",
                options=["Recibido", "En Proceso", "Terminación", "Despacho"],
                value=u.etapa,
                key=f"prod_{u.codigo_xz}"
            )
            
            if st.button(f"📄 Generar PDF #{u.pedido_id:03d}", key=f"pdf_{u.codigo_xz}"):
                archivo = crear_pdf_cotizacion(u.codigo_xz, u.modelo, u.pedido_id)
                with open(archivo, "rb") as f:
                    st.download_button("⬇️ Descargar", f, file_name=archivo, key=f"dl_{u.codigo_xz}")

            if nueva_etapa != u.etapa:
                u.etapa = nueva_etapa
                u.ultima_actualizacion = datetime.now()
                session.commit()
                st.rerun()

st.divider()
st.caption("Grupo I - Normalización y Metrología | Análisis de Criticidad FIFO")