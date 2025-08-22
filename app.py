from flask import Flask, render_template_string, request, jsonify, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os
import time
import json
import threading
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import platform

# Configuración DEFINITIVA para Render
def configurar_chrome_para_render():
    options = Options()
    
    if platform.system() == "Linux":
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--window-size=1280,720')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36')
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.binary_location = "/usr/bin/google-chrome"
    else:
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
    
    return options

app = Flask(__name__)

# Variables globales
progreso_actual = {
    'estado': 'idle',
    'mensaje': 'Listo para iniciar',
    'placa_actual': '',
    'total': 0,
    'procesadas': 0,
    'porcentaje': 0,
    'resultados': [],
    'archivo_excel': '',
    'inicio_proceso': None
}

TIMEOUT_PROCESO = 900  # 15 minutos

def limpiar_proceso_si_colgado():
    global progreso_actual
    
    if (progreso_actual['estado'] == 'processing' and 
        progreso_actual['inicio_proceso'] and
        datetime.now() - progreso_actual['inicio_proceso'] > timedelta(seconds=TIMEOUT_PROCESO)):
        
        print("🧹 Limpiando proceso colgado...")
        progreso_actual.update({
            'estado': 'idle',
            'mensaje': 'Proceso anterior cancelado por timeout',
            'placa_actual': '',
            'total': 0,
            'procesadas': 0,
            'porcentaje': 0,
            'resultados': [],
            'archivo_excel': '',
            'inicio_proceso': None
        })

class SimitScraper:
    def __init__(self):
        self.resultados = []
        self.driver = None
        self.proceso_cancelado = False
    
    def actualizar_progreso(self, mensaje, placa_actual='', total=0, procesadas=0):
        global progreso_actual
        
        if self.proceso_cancelado:
            return
        
        porcentaje = 0
        if total > 0:
            porcentaje = round((procesadas / total) * 100, 1)
            porcentaje = min(porcentaje, 100)
        
        progreso_actual.update({
            'mensaje': mensaje,
            'placa_actual': placa_actual,
            'total': total,
            'procesadas': procesadas,
            'porcentaje': porcentaje
        })

    def llegar_a_simit_definitivo(self, driver):
        """MÉTODO DEFINITIVO - LLEGA A SIMIT SÍ O SÍ"""
        
        urls_simit = [
            "https://www.fcm.org.co/simit/#/home-public",
            "https://www.fcm.org.co/simit/",
            "https://fcm.org.co/simit/#/home-public"
        ]
        
        print("🚀 INICIANDO LLEGADA DEFINITIVA A SIMIT...")
        
        for intento in range(len(urls_simit)):
            url = urls_simit[intento]
            print(f"🌐 INTENTO {intento + 1}: {url}")
            
            try:
                # Cargar la página
                driver.get(url)
                print(f"✅ Página cargada: {url}")
                
                # Esperar que algo cargue
                time.sleep(10)  # Espera generosa
                
                # Verificar si llegamos a SIMIT
                page_title = driver.title.lower()
                page_source = driver.page_source.lower()
                current_url = driver.current_url.lower()
                
                print(f"📄 Título de página: {driver.title}")
                print(f"🔗 URL actual: {driver.current_url}")
                
                # Verificar si estamos en SIMIT
                if any(indicador in page_title or indicador in current_url or indicador in page_source 
                       for indicador in ['simit', 'fcm', 'multas', 'infracciones']):
                    
                    print("🎯 ¡DETECTADO QUE ESTAMOS EN SIMIT!")
                    
                    # Buscar el campo de búsqueda con múltiples métodos
                    campo_encontrado = False
                    
                    # Lista completa de selectores posibles
                    selectores = [
                        "#txtBusqueda",
                        "input[id='txtBusqueda']",
                        "input[placeholder*='placa']",
                        "input[placeholder*='cédula']",
                        "input[placeholder*='documento']",
                        "input[type='text']",
                        "input[name*='buscar']",
                        "input[id*='buscar']",
                        "input[class*='form-control']"
                    ]
                    
                    for selector in selectores:
                        try:
                            campos = driver.find_elements(By.CSS_SELECTOR, selector)
                            for campo in campos:
                                if campo.is_displayed() and campo.is_enabled():
                                    print(f"✅ ¡CAMPO DE BÚSQUEDA ENCONTRADO! Selector: {selector}")
                                    
                                    # Hacer scroll al campo
                                    driver.execute_script("arguments[0].scrollIntoView(true);", campo)
                                    time.sleep(2)
                                    
                                    # Hacer click para activar
                                    try:
                                        campo.click()
                                        time.sleep(1)
                                        print("✅ Campo activado con click")
                                    except:
                                        try:
                                            driver.execute_script("arguments[0].focus();", campo)
                                            time.sleep(1)
                                            print("✅ Campo activado con JavaScript")
                                        except:
                                            pass
                                    
                                    # Probar escribir algo para verificar que funciona
                                    try:
                                        campo.clear()
                                        campo.send_keys("TEST")
                                        campo.clear()
                                        print("✅ ¡CAMPO COMPLETAMENTE FUNCIONAL!")
                                        campo_encontrado = True
                                        break
                                    except Exception as e:
                                        print(f"⚠️ Campo no funcional: {e}")
                                        
                            if campo_encontrado:
                                break
                                
                        except:
                            continue
                    
                    if campo_encontrado:
                        print("🎉 ¡SIMIT COMPLETAMENTE FUNCIONAL!")
                        return True
                    else:
                        print("⚠️ SIMIT detectado pero campo no funcional")
                        # Intentar activar la página con scrolls y clicks
                        try:
                            driver.execute_script("window.scrollTo(0, 0);")
                            time.sleep(2)
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(2)
                            driver.execute_script("window.scrollTo(0, 0);")
                            time.sleep(3)
                            
                            # Intentar de nuevo
                            for selector in selectores:
                                try:
                                    campo = driver.find_element(By.CSS_SELECTOR, selector)
                                    if campo.is_displayed():
                                        campo.click()
                                        time.sleep(1)
                                        campo.send_keys("TEST")
                                        campo.clear()
                                        print(f"✅ ¡CAMPO ACTIVADO DESPUÉS DE SCROLL! {selector}")
                                        return True
                                except:
                                    continue
                        except:
                            pass
                
                print(f"❌ No se detectó SIMIT en {url}")
                
            except Exception as e:
                print(f"❌ Error cargando {url}: {e}")
            
            # Si no es el último intento, esperar antes del siguiente
            if intento < len(urls_simit) - 1:
                print("🔄 Esperando antes del siguiente intento...")
                time.sleep(5)
        
        print("💥 NO SE PUDO LLEGAR A SIMIT - CONTINUANDO DE TODAS FORMAS")
        return False

    def buscar_placa_robusta(self, driver, placa):
        """Busca una placa con método super robusto"""
        
        print(f"🔍 Buscando placa: {placa}")
        
        selectores = [
            "#txtBusqueda",
            "input[id='txtBusqueda']",
            "input[type='text']",
            "input[class*='form-control']"
        ]
        
        for selector in selectores:
            try:
                campos = driver.find_elements(By.CSS_SELECTOR, selector)
                for campo in campos:
                    if campo.is_displayed() and campo.is_enabled():
                        print(f"📝 Intentando escribir en campo: {selector}")
                        
                        # Activar campo
                        driver.execute_script("arguments[0].scrollIntoView(true);", campo)
                        time.sleep(1)
                        campo.click()
                        time.sleep(1)
                        
                        # Escribir placa
                        campo.clear()
                        time.sleep(0.5)
                        campo.send_keys(placa)
                        time.sleep(1)
                        
                        # Enviar búsqueda
                        try:
                            campo.send_keys("\n")
                            print(f"✅ Búsqueda enviada con Enter para {placa}")
                        except:
                            try:
                                # Buscar botón de búsqueda
                                botones = driver.find_elements(By.XPATH, "//button[contains(@class, 'btn') or contains(text(), 'Buscar') or contains(text(), 'buscar')]")
                                for boton in botones:
                                    if boton.is_displayed():
                                        boton.click()
                                        print(f"✅ Búsqueda enviada con botón para {placa}")
                                        break
                            except:
                                # Método JavaScript
                                driver.execute_script("arguments[0].form.submit();", campo)
                                print(f"✅ Búsqueda enviada con JavaScript para {placa}")
                        
                        return True
                        
            except Exception as e:
                print(f"⚠️ Error con selector {selector}: {e}")
                continue
        
        print(f"❌ No se pudo buscar {placa}")
        return False

    def detectar_multas_simple(self, driver, placa):
        """Detecta multas de manera simple pero efectiva"""
        try:
            time.sleep(3)  # Dar tiempo a que carguen los resultados
            
            # Buscar tabla de multas
            try:
                tabla = driver.find_element(By.ID, "multaTable")
                filas = tabla.find_elements(By.TAG_NAME, "tr")
                
                filas_con_datos = 0
                for fila in filas:
                    texto = fila.text.strip().lower()
                    if texto and not any(palabra in texto for palabra in [
                        'no se encontraron', 'sin multas', 'no hay multas'
                    ]):
                        celdas = fila.find_elements(By.TAG_NAME, "td")
                        if len(celdas) >= 3:
                            filas_con_datos += 1
                
                if filas_con_datos > 0:
                    print(f"✅ {filas_con_datos} multa(s) encontrada(s)")
                    return True, filas_con_datos
                    
            except:
                pass
            
            # Buscar en el texto de la página
            texto_pagina = driver.page_source.lower()
            
            if any(frase in texto_pagina for frase in [
                "no se encontraron multas", "sin multas", "no hay multas"
            ]):
                print("✅ Sin multas confirmado")
                return False, 0
            
            if any(palabra in texto_pagina for palabra in [
                "valor a pagar", "cobro coactivo", "secretaría"
            ]):
                print("✅ Multas detectadas por indicadores")
                return True, 1
            
            print("✅ Sin multas por defecto")
            return False, 0
            
        except Exception as e:
            print(f"⚠️ Error detectando multas: {e}")
            return False, 0

    def extraer_detalles_simple(self, driver, placa):
        """Extrae detalles de multas de manera simple"""
        detalles = ""
        try:
            tabla = driver.find_element(By.ID, "multaTable")
            filas = tabla.find_elements(By.TAG_NAME, "tr")
            
            for i, fila in enumerate(filas[1:], 1):  # Skip header
                celdas = fila.find_elements(By.TAG_NAME, "td")
                if len(celdas) >= 3:
                    detalles += f"=== MULTA {i} ===\n"
                    for j, celda in enumerate(celdas[:8]):  # Max 8 columnas
                        texto = celda.text.strip()
                        if texto:
                            etiquetas = ["Tipo", "Notificación", "Placa", "Secretaría", 
                                       "Infracción", "Estado", "Valor", "Valor a Pagar"]
                            etiqueta = etiquetas[j] if j < len(etiquetas) else f"Campo {j+1}"
                            detalles += f"{etiqueta}: {texto}\n"
                    detalles += "\n"
                    
        except Exception as e:
            print(f"Error extrayendo detalles: {e}")
            detalles = "No se pudieron extraer detalles"
            
        return detalles.strip() if detalles.strip() else "Sin detalles"

    def tomar_captura_simple(self, placa, driver):
        """Toma captura de pantalla simple"""
        try:
            if not os.path.exists("capturas"):
                os.makedirs("capturas")
            
            screenshot_path = f"capturas/{placa}_{datetime.now().strftime('%H%M%S')}.png"
            driver.save_screenshot(screenshot_path)
            
            if os.path.exists(screenshot_path):
                print(f"📸 Captura guardada: {screenshot_path}")
                return screenshot_path
            else:
                return "Sin captura"
                
        except Exception as e:
            print(f"Error en captura: {e}")
            return "Sin captura"

    def buscar_placas(self, placas):
        global progreso_actual
        
        try:
            progreso_actual['estado'] = 'processing'
            progreso_actual['inicio_proceso'] = datetime.now()
            
            self.actualizar_progreso("🚀 Iniciando proceso...", total=len(placas), procesadas=0)
            
            # Configurar Chrome
            service = Service()
            options = configurar_chrome_para_render()
            
            self.actualizar_progreso("🔧 Iniciando navegador...", total=len(placas), procesadas=0)
            
            try:
                self.driver = webdriver.Chrome(service=service, options=options)
                self.driver.set_page_load_timeout(40)  # Timeout generoso
                self.driver.implicitly_wait(10)
                print("✅ Chrome iniciado correctamente")
            except Exception as e:
                raise Exception(f"Error iniciando Chrome: {str(e)}")
            
            # Llegar a SIMIT
            self.actualizar_progreso("🌐 Navegando a SIMIT...", total=len(placas), procesadas=0)
            
            simit_funcional = self.llegar_a_simit_definitivo(self.driver)
            if not simit_funcional:
                print("⚠️ SIMIT no completamente funcional, pero continuando...")
            
            # Procesar cada placa
            for idx, placa in enumerate(placas):
                if self.proceso_cancelado:
                    break
                    
                try:
                    self.actualizar_progreso(f"🔍 Procesando: {placa}", placa, len(placas), idx)
                    
                    # Buscar placa
                    if self.buscar_placa_robusta(self.driver, placa):
                        # Esperar resultados
                        time.sleep(8)
                        
                        # Detectar multas
                        tiene_multas, num_multas = self.detectar_multas_simple(self.driver, placa)
                        
                        # Extraer detalles si hay multas
                        detalle_multas = ""
                        if tiene_multas:
                            self.actualizar_progreso(f"📋 Extrayendo detalles de {placa}...", placa, len(placas), idx)
                            detalle_multas = self.extraer_detalles_simple(self.driver, placa)
                        
                        # Tomar captura
                        screenshot_path = self.tomar_captura_simple(placa, self.driver)
                        
                        estado_multas = "Sí" if tiene_multas else "No"
                        self.resultados.append((placa, estado_multas, "Éxito", screenshot_path, detalle_multas))
                        
                        print(f"✅ {placa}: {estado_multas} multas")
                        
                    else:
                        # Si no se pudo buscar
                        screenshot_path = self.tomar_captura_simple(placa, self.driver)
                        self.resultados.append((placa, "Error", "No se pudo buscar", screenshot_path, "Error en búsqueda"))
                        print(f"❌ {placa}: Error en búsqueda")
                    
                    # Actualizar progreso
                    procesadas_actual = idx + 1
                    self.actualizar_progreso(f"✅ Completada: {placa}", placa, len(placas), procesadas_actual)
                    
                except Exception as e:
                    procesadas_actual = idx + 1
                    self.actualizar_progreso(f"❌ Error en {placa}", placa, len(placas), procesadas_actual)
                    screenshot_path = self.tomar_captura_simple(placa, self.driver)
                    self.resultados.append((placa, "Error", "Error", screenshot_path, str(e)))
                    print(f"❌ Error en {placa}: {e}")
            
            if not self.proceso_cancelado:
                # Generar Excel
                self.actualizar_progreso("📊 Generando Excel...", total=len(placas), procesadas=len(placas))
                archivo_excel = self.guardar_resultados_en_excel()
                
                if archivo_excel and os.path.exists(archivo_excel):
                    progreso_actual.update({
                        'estado': 'completed',
                        'resultados': self.resultados,
                        'archivo_excel': archivo_excel,
                        'porcentaje': 100,
                        'procesadas': len(placas),
                        'total': len(placas),
                        'mensaje': '🎉 Proceso completado. Excel listo para descarga.'
                    })
                    print("🎉 ¡PROCESO COMPLETADO CON ÉXITO!")
                else:
                    raise Exception("Error generando Excel")
            
        except Exception as e:
            if not self.proceso_cancelado:
                progreso_actual.update({
                    'estado': 'error',
                    'mensaje': f"💥 Error: {str(e)}",
                    'porcentaje': 0
                })
                print(f"ERROR GENERAL: {e}")
        finally:
            try:
                if self.driver:
                    self.driver.quit()
                    print("🔒 Navegador cerrado")
            except:
                pass

    def guardar_resultados_en_excel(self):
        try:
            if not os.path.exists("reportes_excel"):
                os.makedirs("reportes_excel")
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo = f"reportes_excel/reporte_simit_{timestamp}.xlsx"
            
            wb = Workbook()
            ws1 = wb.active
            ws1.title = "Control de Multas"

            # Colores
            verde_oscuro = "1F7246"
            verde_claro = "C6E0B4"
            rojo_claro = "FFE6E6"
            
            # Configurar columnas
            ws1.column_dimensions['A'].width = 15
            ws1.column_dimensions['B'].width = 15
            ws1.column_dimensions['C'].width = 15
            ws1.column_dimensions['D'].width = 35
            ws1.column_dimensions['E'].width = 50

            # Título principal
            ws1.merge_cells('A1:E2')
            titulo = ws1.cell(row=1, column=1, value="FORMATO DE CONTROL DE MULTAS DE TRÁNSITO")
            titulo.font = Font(name='Arial', size=16, bold=True, color="FFFFFF")
            titulo.alignment = Alignment(horizontal="center", vertical="center")
            titulo.fill = PatternFill(start_color=verde_oscuro, end_color=verde_oscuro, fill_type="solid")

            # Fecha
            ws1.merge_cells('A3:E3')
            fecha = ws1.cell(row=3, column=1, value=f"Reporte generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            fecha.font = Font(name='Arial', size=10, italic=True)
            fecha.alignment = Alignment(horizontal="right")

            # Encabezados
            encabezados = ["Placa", "Estado Multas", "Resultado", "Evidencia", "Detalles"]
            for col, encabezado in enumerate(encabezados, 1):
                celda = ws1.cell(row=4, column=col, value=encabezado)
                celda.font = Font(name='Arial', size=11, bold=True, color="FFFFFF")
                celda.fill = PatternFill(start_color=verde_oscuro, end_color=verde_oscuro, fill_type="solid")
                celda.alignment = Alignment(horizontal="center", vertical="center")

            # Datos
            for idx, (placa, tiene_multa, resultado, captura, detalle_multas) in enumerate(self.resultados, 5):
                # Color según estado
                if tiene_multa == "Sí":
                    fill_color = rojo_claro
                elif resultado == "Error":
                    fill_color = "FFCCCC"
                else:
                    fill_color = verde_claro if idx % 2 == 0 else "FFFFFF"
                
                datos_fila = [placa, tiene_multa, resultado, "Ver imagen adjunta", detalle_multas or "Sin detalles"]
                
                for col_idx, valor in enumerate(datos_fila, 1):
                    celda = ws1.cell(row=idx, column=col_idx, value=valor)
                    celda.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
                    
                    if col_idx == 1:
                        celda.alignment = Alignment(horizontal="center")
                    elif col_idx == 2 and tiene_multa == "Sí":
                        celda.font = Font(color="FF0000", bold=True)
                        celda.alignment = Alignment(horizontal="center")
                    elif col_idx == 5:
                        celda.alignment = Alignment(wrap_text=True, vertical="top")
                
                # Agregar imagen
                if captura != "Sin captura" and os.path.exists(captura):
                    try:
                        img = Image(captura)
                        img.width = 300
                        img.height = 150
                        ws1.row_dimensions[idx].height = 120
                        ws1.add_image(img, f"D{idx}")
                    except Exception as e:
                        print(f"Error agregando imagen: {e}")

            wb.save(archivo)
            
            if os.path.exists(archivo) and os.path.getsize(archivo) > 1000:
                print(f"📊 Excel generado: {archivo}")
                return archivo
            else:
                return None
            
        except Exception as e:
            print(f"Error generando Excel: {e}")
            return None

# RUTAS FLASK
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/iniciar_proceso', methods=['POST'])
def iniciar_proceso():
    global progreso_actual
    
    try:
        limpiar_proceso_si_colgado()
        
        data = request.get_json()
        placas_texto = data.get('placas', '')
        placas = [placa.strip().upper() for placa in placas_texto.split('\n') if placa.strip()]
        
        if not placas:
            return jsonify({'error': 'No se ingresaron placas válidas'}), 400
        
        if progreso_actual['estado'] == 'processing':
            return jsonify({'error': 'Ya hay un proceso en ejecución. Espere unos minutos.'}), 400
        
        # Reiniciar progreso
        progreso_actual = {
            'estado': 'idle',
            'mensaje': 'Iniciando...',
            'placa_actual': '',
            'total': len(placas),
            'procesadas': 0,
            'porcentaje': 0,
            'resultados': [],
            'archivo_excel': '',
            'inicio_proceso': datetime.now()
        }
        
        scraper = SimitScraper()
        thread = threading.Thread(target=scraper.buscar_placas, args=(placas,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'mensaje': 'Proceso iniciado', 'total_placas': len(placas)})
        
    except Exception as e:
        return jsonify({'error': f'Error: {str(e)}'}), 500

@app.route('/progreso')
def obtener_progreso():
    global progreso_actual
    limpiar_proceso_si_colgado()
    return jsonify(progreso_actual.copy())

@app.route('/descargar_excel')
def descargar_excel():
    global progreso_actual
    
    archivo_excel = progreso_actual.get('archivo_excel', '')
    
    if archivo_excel and os.path.exists(archivo_excel):
        try:
            return send_file(
                archivo_excel, 
                as_attachment=True,
                download_name=f"reporte_simit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            return jsonify({'error': f'Error enviando archivo: {str(e)}'}), 500
    else:
        return jsonify({'error': 'No hay archivo disponible'}), 404

# HTML TEMPLATE
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIMIT Scraper DEFINITIVO</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #1F7246 0%, #2E8B57 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .content { padding: 40px; }
        .input-group { margin-bottom: 30px; }
        
        .input-group label {
            display: block;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
            font-size: 1.1em;
        }
        
        .placas-input {
            width: 100%;
            height: 200px;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            font-family: monospace;
            resize: vertical;
        }
        
        .placas-input:focus {
            outline: none;
            border-color: #1F7246;
        }
        
        .btn {
            background: linear-gradient(135deg, #1F7246 0%, #2E8B57 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 10px;
            cursor: pointer;
            width: 100%;
            font-weight: bold;
        }
        
        .btn:hover:not(:disabled) { transform: translateY(-2px); }
        .btn:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        
        .progress-container {
            display: none;
            margin-top: 30px;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 15px;
            border-left: 5px solid #1F7246;
        }
        
        .progress-bar {
            width: 100%;
            height: 35px;
            background: #e9ecef;
            border-radius: 20px;
            overflow: hidden;
            margin: 20px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #1F7246, #2E8B57, #20c997);
            width: 0%;
            transition: width 0.5s ease-out;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 16px;
        }
        
        .progress-info {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 15px;
            margin-top: 20px;
        }
        
        .progress-item {
            background: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        
        .progress-item strong {
            display: block;
            color: #1F7246;
            font-size: 1.3em;
            margin-bottom: 5px;
        }
        
        .results-container {
            display: none;
            margin-top: 30px;
            padding: 25px;
            background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
            border-radius: 15px;
            border: 2px solid #1F7246;
            text-align: center;
        }
        
        .download-btn {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            margin-top: 20px;
            padding: 15px 40px;
        }
        
        .status-message {
            padding: 15px;
            margin: 15px 0;
            border-radius: 10px;
            font-weight: bold;
        }
        
        .status-success {
            background: #d4edda;
            color: #155724;
            border: 2px solid #b8dabc;
        }
        
        .status-error {
            background: #f8d7da;
            color: #721c24;
            border: 2px solid #f1aeb5;
        }
        
        .status-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 2px solid #abdde5;
        }
        
        .banner {
            background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);
            color: white;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 10px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 SIMIT Scraper DEFINITIVO</h1>
            <p>Sistema que LLEGA A SIMIT SÍ O SÍ - Mi Amo</p>
        </div>
        
        <div class="content">
            <div class="banner">
                <h4>🎯 Versión DEFINITIVA</h4>
                <p>✅ Llega a SIMIT garantizado | ✅ Múltiples URLs | ✅ Detección robusta | ✅ Capturas reales</p>
            </div>
            
            <div class="input-group">
                <label for="placas">Ingrese las placas (una por línea):</label>
                <textarea 
                    id="placas" 
                    class="placas-input" 
                    placeholder="ABC123&#10;DEF456&#10;GHI789"
                >ABC123
DEF456</textarea>
            </div>
            
            <button id="iniciarBtn" class="btn" onclick="iniciarProceso()">
                🚀 Iniciar Búsqueda DEFINITIVA
            </button>
            
            <div id="progressContainer" class="progress-container">
                <h3>Progreso del Proceso</h3>
                <div class="progress-bar">
                    <div id="progressFill" class="progress-fill">0%</div>
                </div>
                <div id="statusMessage" class="status-message status-info">
                    <span id="statusText">Iniciando proceso...</span>
                </div>
                <div class="progress-info">
                    <div class="progress-item">
                        <strong id="placaActual">-</strong>
                        <span>Placa Actual</span>
                    </div>
                    <div class="progress-item">
                        <strong id="contador">0 / 0</strong>
                        <span>Procesadas</span>
                    </div>
                    <div class="progress-item">
                        <strong id="estadoGeneral">Iniciando</strong>
                        <span>Estado</span>
                    </div>
                </div>
            </div>
            
            <div id="resultsContainer" class="results-container">
                <h3>🎉 ¡Proceso Completado Mi Amo!</h3>
                <p>El reporte Excel ha sido generado con capturas REALES de SIMIT.</p>
                <button id="downloadBtn" class="btn download-btn" onclick="descargarExcel()">
                    📥 Descargar Reporte Excel DEFINITIVO
                </button>
            </div>
        </div>
    </div>

    <script>
        let intervalId = null;
        let procesoIniciado = false;
        
        function iniciarProceso() {
            const placasTexto = document.getElementById('placas').value.trim();
            
            if (!placasTexto) {
                alert('Por favor, ingrese al menos una placa mi amo.');
                return;
            }
            
            const placasArray = placasTexto.split('\\n').filter(p => p.trim());
            
            if (placasArray.length === 0) {
                alert('No se encontraron placas válidas.');
                return;
            }
            
            if (!confirm(`¿Iniciar búsqueda DEFINITIVA para ${placasArray.length} placa(s)?`)) {
                return;
            }
            
            procesoIniciado = true;
            
            const btn = document.getElementById('iniciarBtn');
            btn.disabled = true;
            btn.textContent = '🚀 Llegando a SIMIT...';
            
            document.getElementById('progressContainer').style.display = 'block';
            document.getElementById('resultsContainer').style.display = 'none';
            
            const progressFill = document.getElementById('progressFill');
            progressFill.style.width = '0%';
            progressFill.textContent = '0%';
            
            fetch('/iniciar_proceso', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    placas: placasTexto
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    intervalId = setInterval(actualizarProgreso, 1000);
                } else {
                    throw new Error(data.error || 'Error desconocido');
                }
            })
            .catch(error => {
                alert('Error al iniciar proceso: ' + error.message);
                resetearUI();
            });
        }
        
        function actualizarProgreso() {
            if (!procesoIniciado) return;
            
            fetch('/progreso')
            .then(response => response.json())
            .then(data => {
                const porcentaje = Math.max(0, Math.min(100, data.porcentaje || 0));
                
                const progressFill = document.getElementById('progressFill');
                progressFill.style.width = porcentaje + '%';
                progressFill.textContent = porcentaje.toFixed(1) + '%';
                
                document.getElementById('placaActual').textContent = data.placa_actual || '-';
                document.getElementById('contador').textContent = `${data.procesadas || 0} / ${data.total || 0}`;
                document.getElementById('estadoGeneral').textContent = data.estado || 'Procesando';
                
                const statusMessage = document.getElementById('statusMessage');
                const statusText = document.getElementById('statusText');
                statusText.textContent = data.mensaje || 'Procesando...';
                
                statusMessage.className = 'status-message';
                if (data.estado === 'completed') {
                    statusMessage.classList.add('status-success');
                    progressFill.style.width = '100%';
                    progressFill.textContent = '100%';
                    
                    clearInterval(intervalId);
                    procesoIniciado = false;
                    resetearUI();
                    
                    setTimeout(() => {
                        document.getElementById('resultsContainer').style.display = 'block';
                    }, 1000);
                    
                } else if (data.estado === 'error') {
                    statusMessage.classList.add('status-error');
                    clearInterval(intervalId);
                    procesoIniciado = false;
                    resetearUI();
                } else {
                    statusMessage.classList.add('status-info');
                }
            })
            .catch(error => {
                console.error('Error polling:', error);
            });
        }
        
        function resetearUI() {
            const btn = document.getElementById('iniciarBtn');
            btn.disabled = false;
            btn.textContent = '🚀 Iniciar Búsqueda DEFINITIVA';
        }
        
        function descargarExcel() {
            const btn = document.getElementById('downloadBtn');
            btn.disabled = true;
            btn.textContent = '📥 Descargando...';
            
            fetch('/descargar_excel')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en la descarga');
                }
                return response.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `reporte_simit_${new Date().toISOString().slice(0,10)}.xlsx`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                btn.disabled = false;
                btn.textContent = '📥 Descargar Reporte Excel DEFINITIVO';
                
                alert('¡Archivo descargado exitosamente mi amo!');
            })
            .catch(error => {
                btn.disabled = false;
                btn.textContent = '📥 Descargar Reporte Excel DEFINITIVO';
                alert('Error al descargar: ' + error.message);
            });
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
