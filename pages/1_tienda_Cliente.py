import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import hashlib

# --- DB SETUP ---
engine = create_engine('sqlite:///trazabilidad_v2.db')
Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True)
    password = Column(String)
    nombre = Column(String)

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

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- DATOS PRODUCTOS ---
PRODUCTOS_INFO = {
    "Apex-15 Stealth": {"img": "images/Apex-15Stealth.webp", "precio": 85900, "specs": "💻 i7-13700H | RTX 4070"},
    "Titan-18 Ultra": {"img": "images/Titan18Ultra.webp", "precio": 145000, "specs": "🚀 i9-14900HX | RTX 4090"},
    "Horizon-G Pro": {"img": "images/HorizonG-pro.webp", "precio": 95000, "specs": "🖥️ Ryzen 9 | RTX 4080"},
    "Workstation-X": {"img": "images/WorkstationX.png", "precio": 110000, "specs": "🦾 Xeon Gold | Quadro RTX"},
    "GPU-Vortex 90": {"img": "images/GpuVortex.webp", "precio": 62500, "specs": "⚙️ 24GB GDDR6X | DLSS 3.5"},
    "RAM-Fury 64GB": {"img": "images/RAM-Fury-64gb.webp", "precio": 18200, "specs": "⚡ DDR5 6000MHz | RGB"}
}

st.set_page_config(page_title="TechArmor Store", layout="wide")

# Inicializar estados de sesión
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'carrito' not in st.session_state: st.session_state.carrito = []

# --- BARRA LATERAL (REGISTRO Y LOGIN) ---
with st.sidebar:
    st.title("👤 Mi Cuenta")
    if not st.session_state.logged_in:
        with st.expander("📝 Registrarse", expanded=False):
            with st.form("reg_form"):
                n_nom = st.text_input("Nombre")
                n_em = st.text_input("Email")
                n_pw = st.text_input("Clave", type="password")
                if st.form_submit_button("Crear Cuenta"):
                    try:
                        u = Usuario(nombre=n_nom, email=n_em, password=hash_password(n_pw))
                        session.add(u); session.commit()
                        st.success("¡Cuenta creada! Ya puedes comprar.")
                    except: st.error("Email ya existe.")
        st.info("Inicia sesión al finalizar tu compra.")
    else:
        st.success(f"Bienvenido, {st.session_state.user_email}")
        if st.button("Cerrar Sesión"):
            st.session_state.logged_in = False
            st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.title("🛡️ TechArmor Premium Systems")

tab_comprar, tab_rastrear = st.tabs(["🛒 Catálogo", "🔍 Mis Órdenes"])

with tab_comprar:
    col_prod, col_cart = st.columns([3, 1.2])
    
    with col_prod:
        p_list = list(PRODUCTOS_INFO.items())
        for row in range(0, len(p_list), 2):
            cols = st.columns(2)
            for i in range(2):
                if row + i < len(p_list):
                    name, info = p_list[row+i]
                    with cols[i]:
                        if os.path.exists(info["img"]): st.image(info["img"], use_container_width=True)
                        st.subheader(name)
                        st.write(f"RD$ {info['precio']:,}")
                        if st.button(f"Añadir", key=f"add_{name}"):
                            st.session_state.carrito.append(name)
                            st.toast(f"✅ {name} añadido")

    with col_cart:
        st.subheader("Tu Carrito")
        if not st.session_state.carrito:
            st.info("Vacío")
        else:
            for idx, item in enumerate(st.session_state.carrito):
                c1, c2 = st.columns([4, 1])
                c1.write(item)
                if c2.button("🗑️", key=f"del_{idx}"):
                    st.session_state.carrito.pop(idx)
                    st.rerun()
            
            total = sum([PRODUCTOS_INFO[i]['precio'] for i in st.session_state.carrito])
            st.divider()
            st.write(f"### Total: RD$ {total:,}")

            if st.button("🚀 Proceder al Pago", use_container_width=True):
                if not st.session_state.logged_in:
                    st.session_state.mostrar_login = True
                else:
                    st.session_state.proceder_compra = True

            if not st.session_state.logged_in and st.session_state.get('mostrar_login', False):
                with st.form("login_pago"):
                    st.write("🔑 **Ingresa para completar la compra**")
                    le = st.text_input("Email")
                    lp = st.text_input("Password", type="password")
                    if st.form_submit_button("Entrar y Pagar"):
                        user = session.query(Usuario).filter(Usuario.email==le, Usuario.password==hash_password(lp)).first()
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.user_email = le
                            st.session_state.user_id = user.id
                            st.session_state.proceder_compra = True
                            st.rerun()
                        else: st.error("Datos incorrectos")

            if st.session_state.logged_in and st.session_state.get('proceder_compra', False):
                np = Pedido(usuario_id=st.session_state.user_id)
                session.add(np); session.commit()
                for p_name in st.session_state.carrito:
                    id_u = f"XZ-{p_name[:2].upper()}-{datetime.now().strftime('%M%S')}"
                    session.add(Unidad(codigo_xz=id_u, modelo=p_name, etapa="Recibido", pedido_id=np.id))
                session.commit()
                st.success(f"¡Orden #{np.id} exitosa!")
                st.session_state.carrito = []
                st.session_state.proceder_compra = False
                st.balloons()

with tab_rastrear:
    st.subheader("Historial de Trazabilidad")
    if not st.session_state.logged_in:
        st.info("Inicia sesión para ver tus pedidos.")
    else:
        num = st.number_input("Número de orden:", min_value=1, step=1)
        if st.button("Rastrear"):
            res = session.query(Unidad).filter(Unidad.pedido_id == num).all()
            if res:
                for item in res:
                    st.write(f"📦 {item.modelo} - **{item.etapa}**")
                    st.progress({"Recibido": 15, "En Proceso": 50, "Terminación": 85, "Despacho": 100}.get(item.etapa, 0))
            else: st.error("No se encontró la orden.")