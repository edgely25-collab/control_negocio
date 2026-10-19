import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="BeniFerch - Control",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #4F46E5;
        margin-bottom: 10px;
    }
    .metric-title { font-size: 14px; color: #6B7280; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 24px; font-weight: 700; color: #111827; }
    .stButton>button {
        width: 100%;
        background-color: #4F46E5;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        padding: 10px 16px;
    }
    .stButton>button:hover { background-color: #4338CA; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN A BASE DE DATOS Y MIGRACIÓN ---
conn = sqlite3.connect("negocio.db", check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS inventario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto TEXT NOT NULL,
                    stock INTEGER DEFAULT 0,
                    precio_costo REAL,
                    precio_venta REAL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS adeudos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente TEXT NOT NULL,
                    concepto TEXT,
                    monto_total REAL,
                    saldo_pendiente REAL,
                    fecha TEXT,
                    estado TEXT DEFAULT 'PENDIENTE'
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS pagos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    adeudo_id INTEGER,
                    monto_abono REAL,
                    fecha TEXT,
                    FOREIGN KEY(adeudo_id) REFERENCES adeudos(id)
                )''')
    conn.commit()

# Esta función actualiza tu tabla antigua agregando las columnas de control de inventario
def upgrade_db():
    try:
        c.execute("ALTER TABLE inventario ADD COLUMN stock_inicial INTEGER DEFAULT 0")
        c.execute("ALTER TABLE inventario ADD COLUMN entradas INTEGER DEFAULT 0")
        c.execute("ALTER TABLE inventario ADD COLUMN salidas INTEGER DEFAULT 0")
        # Ajusta los productos existentes para que su stock actual sea el inicial
        c.execute("UPDATE inventario SET stock_inicial = stock WHERE stock_inicial = 0 AND entradas = 0 AND salidas = 0")
        conn.commit()
    except Exception:
        pass # Si las columnas ya existen, ignora el error

init_db()
upgrade_db()

# --- BARRA LATERAL CON LOGO Y NAVEGACIÓN ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/design.png", width=70)
    st.title("BeniFerch")
    st.caption("Joyitas y Estampados - Control de Negocio")
    st.divider()
    
    opciones_menu = ["📊 Resumen General", "📦 Inventario", "📥 Recepción de Inventario", "💳 Cuentas por Cobrar", "➕ Nuevo Registro", "✏️ Editar / Borrar"]
    opcion = st.radio("Navegación", opciones_menu)

# --- HEADER PRINCIPAL ---
st.title("📱 Panel de Control")

# --- OPCIÓN 1: RESUMEN GENERAL ---
if opcion == "📊 Resumen General":
    st.subheader("Estado Financiero y Stock")
    
    df_inv = pd.read_sql("SELECT * FROM inventario", conn)
    df_adeudos = pd.read_sql("SELECT * FROM adeudos WHERE estado = 'PENDIENTE'", conn)
    
    total_articulos = df_inv['stock'].sum() if not df_inv.empty else 0
    valor_inventario = (df_inv['stock'] * df_inv['precio_costo']).sum() if not df_inv.empty else 0
    total_adeudos = df_adeudos['saldo_pendiente'].sum() if not df_adeudos.empty else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Unidades en Stock Actual</div>
            <div class="metric-value">{total_articulos} pcs</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Valor en Inventario</div>
            <div class="metric-value">${valor_inventario:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #EF4444;">
        <div class="metric-title">Por Cobrar (Adeudos)</div>
        <div class="metric-value" style="color: #DC2626;">${total_adeudos:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# --- OPCIÓN 2: INVENTARIO (NUEVAS COLUMNAS) ---
elif opcion == "📦 Inventario":
    st.subheader("Catálogo de Productos")
    
    df_inv = pd.read_sql("SELECT id as 'ID', producto as 'Producto', precio_costo as 'Costo ($)', precio_venta as 'Venta ($)', stock_inicial as 'Inv. Inicial', entradas as 'Recepción (+)', salidas as 'Ventas (-)', stock as 'Inv. Final' FROM inventario", conn)
    
    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
    else:
        st.info("No hay productos registrados aún.")

# --- OPCIÓN 3: RECEPCIÓN DE INVENTARIO ---
elif opcion == "📥 Recepción de Inventario":
    st.subheader("Ingresar Mercancía (Resurtir)")
    
    df_inv = pd.read_sql("SELECT * FROM inventario", conn)
    if not df_inv.empty:
        prod_id = st.selectbox("Selecciona el Producto a Resurtir", df_inv['id'].tolist(), format_func=lambda x: f"ID {x} - {df_inv[df_inv['id']==x]['producto'].values[0]} (Stock actual: {df_inv[df_inv['id']==x]['stock'].values[0]})")
        
        # Formulario que se limpia al guardar
        with st.form("form_recepcion", clear_on_submit=True):
            cant_agregar = st.number_input("Cantidad a Ingresar", min_value=1, value=1)
            
            if st.form_submit_button("Guardar Entrada de Inventario"):
                c.execute("UPDATE inventario SET stock = stock + ?, entradas = entradas + ? WHERE id = ?", (cant_agregar, cant_agregar, prod_id))
                conn.commit()
                st.success("Inventario actualizado correctamente.")
                st.rerun()
    else:
        st.warning("Primero debes registrar un producto en 'Nuevo Registro'.")

# --- OPCIÓN 4: ADEUDOS Y ABONOS ---
elif opcion == "💳 Cuentas por Cobrar":
    st.subheader("Adeudos de Clientes")
    
    df_adeudos = pd.read_sql("SELECT id as 'ID', cliente as 'Cliente', concepto as 'Concepto', saldo_pendiente as 'Saldo Pendiente ($)', fecha as 'Fecha' FROM adeudos WHERE estado = 'PENDIENTE'", conn)
    
    if not df_adeudos.empty:
        st.dataframe(df_adeudos, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Registrar Abono")
        adeudo_sel = st.selectbox("Selecciona el Cliente / Folio", df_adeudos['ID'].tolist(), format_func=lambda x: f"ID {x} - {df_adeudos[df_adeudos['ID']==x]['Cliente'].values[0]} (${df_adeudos[df_adeudos['ID']==x]['Saldo Pendiente ($)'].values[0]})")
        
        # Formulario que se limpia al guardar
        with st.form("form_abono", clear_on_submit=True):
            monto_abono = st.number_input("Monto a Abonar ($)", min_value=0.1, step=10.0)
            
            if st.form_submit_button("Registrar Abono"):
                saldo_act = df_adeudos[df_adeudos['ID']==adeudo_sel]['Saldo Pendiente ($)'].values[0]
                nuevo_saldo = saldo_act - monto_abono
                nuevo_estado = "PAGADO" if nuevo_saldo <= 0 else "PENDIENTE"
                
                c.execute("UPDATE adeudos SET saldo_pendiente = ?, estado = ? WHERE id = ?", (max(0.0, nuevo_saldo), nuevo_estado, adeudo_sel))
                c.execute("INSERT INTO pagos (adeudo_id, monto_abono, fecha) VALUES (?, ?, ?)", (adeudo_sel, monto_abono, datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()
                st.success("Abono registrado correctamente.")
                st.rerun()
    else:
        st.success("🎉 ¡No hay cuentas pendientes por cobrar!")

# --- OPCIÓN 5: NUEVO REGISTRO ---
elif opcion == "➕ Nuevo Registro":
    st.subheader("Captura de Información")
    tipo = st.radio("Selecciona qué deseas registrar:", ["Producto Nuevo", "Nuevo Adeudo / Venta"], horizontal=True)
    
    if tipo == "Producto Nuevo":
        # Formulario que se limpia al guardar
        with st.form("form_prod", clear_on_submit=True):
            nombre = st.text_input("Nombre del Producto / Insumo")
            stock = st.number_input("Stock Inicial", min_value=0, value=1)
            costo = st.number_input("Precio de Costo ($)", min_value=0.0, value=0.0)
            venta = st.number_input("Precio de Venta ($)", min_value=0.0, value=0.0)
            
            if st.form_submit_button("Guardar Producto"):
                if nombre:
                    c.execute("INSERT INTO inventario (producto, stock, precio_costo, precio_venta, stock_inicial, entradas, salidas) VALUES (?, ?, ?, ?, ?, 0, 0)", (nombre, stock, costo, venta, stock))
                    conn.commit()
                    st.success(f"Producto '{nombre}' guardado exitosamente.")
                else:
                    st.error("Por favor ingresa el nombre del producto.")
                    
    elif tipo == "Nuevo Adeudo / Venta":
        df_inv = pd.read_sql("SELECT id, producto, stock, precio_venta FROM inventario WHERE stock > 0", conn)
        
        descontar_stock = st.checkbox("¿Descontar un producto del inventario?", value=False)
        prod_seleccionado_id = None
        cant_descontar = 1
        
        if descontar_stock:
            if not df_inv.empty:
                prod_opciones = {row['id']: f"{row['producto']} (Stock: {row['stock']} | Precio: ${row['precio_venta']})" for _, row in df_inv.iterrows()}
                prod_seleccionado_id = st.selectbox("Selecciona el Producto", list(prod_opciones.keys()), format_func=lambda x: prod_opciones[x])
                
                stock_max = int(df_inv[df_inv['id'] == prod_seleccionado_id]['stock'].values[0])
                precio_sugerido = float(df_inv[df_inv['id'] == prod_seleccionado_id]['precio_venta'].values[0])
                
                cant_descontar = st.number_input("Cantidad a entregar/vender", min_value=1, max_value=stock_max, value=1)
                monto_sugerido_total = precio_sugerido * cant_descontar
            else:
                st.warning("No hay productos con stock disponible para descontar.")
                descontar_stock = False
                monto_sugerido_total = 0.0
        else:
            monto_sugerido_total = 0.0

        # Formulario que se limpia al guardar
        with st.form("form_adeudo", clear_on_submit=True):
            cliente = st.text_input("Nombre del Cliente")
            
            if descontar_stock and prod_seleccionado_id:
                prod_nombre = df_inv[df_inv['id'] == prod_seleccionado_id]['producto'].values[0]
                concepto_inicial = f"{cant_descontar}x {prod_nombre}"
            else:
                concepto_inicial = ""
                
            concepto = st.text_input("Concepto / Detalles del trabajo", value=concepto_inicial)
            monto = st.number_input("Monto Total ($)", min_value=0.0, value=float(monto_sugerido_total))
            
            if st.form_submit_button("Guardar Deuda / Venta"):
                if cliente:
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M")
                    c.execute("INSERT INTO adeudos (cliente, concepto, monto_total, saldo_pendiente, fecha) VALUES (?, ?, ?, ?, ?)", (cliente, concepto, monto, monto, fecha_hoy))
                    
                    if descontar_stock and prod_seleccionado_id:
                        c.execute("UPDATE inventario SET stock = stock - ?, salidas = salidas + ? WHERE id = ?", (cant_descontar, cant_descontar, prod_seleccionado_id))
                        
                    conn.commit()
                    st.success(f"Registro exitoso para {cliente}.")
                else:
                    st.error("Por favor ingresa el nombre del cliente.")

# --- OPCIÓN 6: EDITAR Y ELIMINAR (CORRECCIÓN DE NOMBRES Y PRECIOS) ---
elif opcion == "✏️ Editar / Borrar":
    st.subheader("Corrección de Registros")
    sub_opcion = st.radio("¿Qué deseas modificar?", ["Corregir Producto", "Corregir Adeudo"], horizontal=True)
    
    if sub_opcion == "Corregir Producto":
        df_inv = pd.read_sql("SELECT * FROM inventario", conn)
        if not df_inv.empty:
            prod_id = st.selectbox("Selecciona Producto a Corregir", df_inv['id'].tolist(), format_func=lambda x: f"ID {x} - {df_inv[df_inv['id']==x]['producto'].values[0]}")
            
            prod_row = df_inv[df_inv['id'] == prod_id].iloc[0]
            
            with st.form("edit_prod"):
                st.info("Aquí solo puedes editar Nombres y Precios. Usa 'Recepción de Inventario' para agregar stock.")
                e_nombre = st.text_input("Nombre del Producto", value=prod_row['producto'])
                e_costo = st.number_input("Precio Costo ($)", min_value=0.0, value=float(prod_row['precio_costo']))
                e_venta = st.number_input("Precio Venta ($)", min_value=0.0, value=float(prod_row['precio_venta']))
                
                col_save, col_del = st.columns(2)
                
                if col_save.form_submit_button("Guardar Corrección"):
                    c.execute("UPDATE inventario SET producto=?, precio_costo=?, precio_venta=? WHERE id=?", (e_nombre, e_costo, e_venta, prod_id))
                    conn.commit()
                    st.success("Producto corregido correctamente.")
                    st.rerun()
                    
            if st.button("❌ Eliminar Producto Definitivamente"):
                c.execute("DELETE FROM inventario WHERE id=?", (prod_id,))
                conn.commit()
                st.warning("Producto eliminado.")
                st.rerun()
        else:
            st.info("No hay productos para editar.")

    elif sub_opcion == "Corregir Adeudo":
        df_adeudos = pd.read_sql("SELECT * FROM adeudos", conn)
        if not df_adeudos.empty:
            adeudo_id = st.selectbox("Selecciona Registro a Corregir", df_adeudos['id'].tolist(), format_func=lambda x: f"ID {x} - {df_adeudos[df_adeudos['id']==x]['cliente'].values[0]} (${df_adeudos[df_adeudos['id']==x]['saldo_pendiente'].values[0]})")
            
            ad_row = df_adeudos[df_adeudos['id'] == adeudo_id].iloc[0]
            
            with st.form("edit_adeudo"):
                st.info("Solo se permite editar el nombre, concepto y estado para proteger los montos financieros.")
                e_cliente = st.text_input("Nombre del Cliente", value=ad_row['cliente'])
                e_concepto = st.text_input("Concepto / Detalles", value=ad_row['concepto'])
                e_estado = st.selectbox("Estado de la Deuda", ["PENDIENTE", "PAGADO"], index=0 if ad_row['estado'] == "PENDIENTE" else 1)
                
                if st.form_submit_button("Guardar Corrección"):
                    c.execute("UPDATE adeudos SET cliente=?, concepto=?, estado=? WHERE id=?", (e_cliente, e_concepto, e_estado, adeudo_id))
                    conn.commit()
                    st.success("Deuda corregida correctamente.")
                    st.rerun()
                    
            if st.button("❌ Eliminar Registro de Deuda"):
                c.execute("DELETE FROM adeudos WHERE id=?", (adeudo_id,))
                conn.commit()
                st.warning("Registro eliminado.")
                st.rerun()
        else:
            st.info("No hay adeudos para editar.")
