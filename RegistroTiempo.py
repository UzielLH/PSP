import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
import locale
import threading
import time

# Se importan los módulos necesarios de ReportLab para generar el PDF.
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib import colors

# Intenta configurar la localización a español (esto puede fallar en algunos sistemas)
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    # En Windows o si no está disponible 'es_ES.UTF-8', prueba con otra variante
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain')
    except locale.Error:
        pass  # Si falla, usaremos nuestra función personalizada para formatear fechas

class RegistroTiempo(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Registro de Tiempo")
        self.geometry("1000x600")
        self.resizable(False, False)

        # Configuración del estilo usando ttk.
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", font=("Helvetica", 12), padding=6)
        style.configure("Header.TLabel", font=("Helvetica", 16, "bold"))
        style.configure("Title.TLabel", font=("Helvetica", 14))
        style.configure("Time.TLabel", font=("Serif", 24))
        style.configure("Elapsed.TLabel", font=("Serif", 48))

        self.activities_list = ["Analizar", "Planificar", "Codificar", "Testear", 
                                  "Evaluación del código", "Revisión del código", "Lanzamiento",
                                  "Diagramar", "Reunión"]

        self.show_instructions()

        # Seleccionar o crear el archivo de datos (.txt)
        self.filename = self.select_or_create_file()
        self.data = self.load_data()
        self.activities = self.data.get('activities', {})
        self.total_paused_minutes = self.data.get('total_paused_minutes', 0)
        self.activity_logs = self.data.get('activity_logs', [])
        self.project_name = self.data.get('project_name', None)
        self.start_date = self.data.get('start_date', None)

        # Si no hay datos de proyecto (archivo nuevo), se solicitan los detalles.
        if not self.project_name:
            self.project_name, self.start_date = self.get_project_details()
            self.data['project_name'] = self.project_name
            self.data['start_date'] = self.start_date
            self.save_data()

        # -------------------------------
        # Creación de la interfaz con diseño mejorado
        # -------------------------------

        # Etiqueta del proyecto
        self.project_label = ttk.Label(self, text=f"Proyecto: {self.project_name}", style="Header.TLabel", background="lightblue")
        self.project_label.pack(pady=10)

        # Frame para las etiquetas de tiempo
        time_frame = ttk.Frame(self)
        time_frame.pack(pady=5)

        # Hora Actual
        label_current = ttk.Label(time_frame, text="Hora Actual", style="Title.TLabel")
        label_current.grid(row=0, column=0, sticky="W", padx=5, pady=5)
        self.current_time_label = ttk.Label(time_frame, text="00:00:00", style="Time.TLabel")
        self.current_time_label.grid(row=0, column=1, sticky="E", padx=5, pady=5)

        # Tiempo de Actividad
        label_elapsed = ttk.Label(time_frame, text="Tiempo de Actividad", style="Title.TLabel")
        label_elapsed.grid(row=1, column=0, sticky="W", padx=5, pady=5)
        self.elapsed_time_label = ttk.Label(time_frame, text="00:00:00", style="Elapsed.TLabel")
        self.elapsed_time_label.grid(row=1, column=1, sticky="E", padx=5, pady=5)

        # Tiempo en Pausa (se muestra en formato hh:mm:ss)
        label_paused = ttk.Label(time_frame, text="Tiempo en Pausa", style="Title.TLabel")
        label_paused.grid(row=2, column=0, sticky="W", padx=5, pady=5)
        self.paused_time_label = ttk.Label(time_frame, text="00:00:00", style="Time.TLabel")
        self.paused_time_label.grid(row=2, column=1, sticky="E", padx=5, pady=5)

        # Actividad Actual (centrada)
        self.activity_name_label = ttk.Label(self, text="", style="Title.TLabel")
        self.activity_name_label.pack(pady=10)

        # Frame para los botones de control
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=15)

        self.start_button = ttk.Button(button_frame, text="Iniciar", command=self.start_activity)
        self.start_button.grid(row=0, column=0, padx=10)

        self.pause_button = ttk.Button(button_frame, text="Pausar", state="disabled", command=self.pause_activity)
        self.pause_button.grid(row=0, column=1, padx=10)

        self.stop_button = ttk.Button(button_frame, text="Parar", state="disabled", command=self.stop_activity)
        self.stop_button.grid(row=0, column=2, padx=10)

        # Frame para los botones adicionales
        additional_buttons_frame = ttk.Frame(self)
        additional_buttons_frame.pack(pady=10)

        # Botón para producir el PDF (centrado)
        self.pdf_button = ttk.Button(additional_buttons_frame, text="Producir PDF", command=self.produce_pdf, width=20)
        self.pdf_button.grid(row=0, column=0, padx=5, pady=5)

        # Botón para visualizar la tabla de registros
        self.table_button = ttk.Button(additional_buttons_frame, text="Visualizar Tabla", command=self.show_table, width=20)
        self.table_button.grid(row=0, column=1, padx=5, pady=5)

        # Botón para visualizar los gráficos
        self.graph_button = ttk.Button(additional_buttons_frame, text="Visualizar Gráficos", command=self.show_statistics, width=20)
        self.graph_button.grid(row=0, column=2, padx=5, pady=5)

        # Botón para cambiar de proyecto (abrir uno existente o crear uno nuevo)
        self.new_project_button = ttk.Button(additional_buttons_frame, text="Nuevo Proyecto", command=self.change_project, width=20)
        self.new_project_button.grid(row=0, column=3, padx=5, pady=5)

        # Variables para el cronómetro y control de actividad.
        self.start_time = None
        self.pause_time = None
        self.total_paused_time = timedelta()
        self.current_activity = None
        self.paused_minutes = 0
        self.timer_running = False
        self.is_paused = False
        self.activity_comments = ""
        self.notification_shown = False

        self.update_current_time()

    def formatear_fecha(self, dt):
        """
        Formatea un objeto datetime a una cadena con el formato:
        "Día, dd mes aaaa" usando arreglos con los nombres correctos en español.
        """
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                 "septiembre", "octubre", "noviembre", "diciembre"]
        return f"{dias_semana[dt.weekday()]}, {dt.day:02d} {meses[dt.month - 1]} {dt.year}"

    def show_instructions(self):
        instructions = (
            "Registro de tiempos:\n"
            "1.- Es necesario seleccionar un archivo .txt para obtener los datos.\n"
            "2.- Si el archivo no está disponible, se puede cancelar la selección y se abrirá una nueva ventana para crearlo.\n"
            "3.- Al crear un nuevo proyecto, se solicitará el nombre y la fecha de inicio.\n"
            "4.- Al iniciar la actividad, se solicitarán comentarios y el cronómetro comenzará a registrar el tiempo.\n"
            "5.- Si la actividad se pausa, el tiempo seguirá siendo registrado.\n"
            "6.- Al detener la actividad se guardará un registro con la fecha, horas, tiempos en pausa y sin pausa, actividad y comentarios.\n"
            "7.- Después de parar la actividad se mostrarán las gráficas de los tiempos concentrados."
        )
        messagebox.showinfo("Instrucciones", instructions)

    def select_or_create_file(self):
        """
        Pregunta al usuario si desea abrir un proyecto existente o crear uno nuevo,
        y en función de la respuesta utiliza el diálogo de archivo correspondiente.
        """
        respuesta = messagebox.askyesno("Seleccionar Proyecto", 
                                        "¿Desea abrir un proyecto existente?\n(Sí: Abrir | No: Crear uno nuevo)")
        if respuesta:
            file_path = filedialog.askopenfilename(title="Seleccione un archivo de datos", filetypes=[("Text files", "*.txt")])
            if not file_path:
                # Si se cancela la apertura, se procede a crear un nuevo archivo
                file_path = filedialog.asksaveasfilename(title="Crear un nuevo archivo de datos", 
                                                         defaultextension=".txt", 
                                                         filetypes=[("Text files", "*.txt")])
        else:
            file_path = filedialog.asksaveasfilename(title="Crear un nuevo archivo de datos", 
                                                     defaultextension=".txt", 
                                                     filetypes=[("Text files", "*.txt")])
        return file_path

    def get_project_details(self):
        # Validar que el nombre del proyecto no esté vacío.
        while True:
            project_name = simpledialog.askstring("Nuevo Proyecto", "Ingrese el nombre del proyecto:")
            if project_name:
                break
            else:
                messagebox.showerror("Error", "El nombre del proyecto no puede estar vacío. Intente nuevamente.")
        
        # Validación de la fecha en el formato dd/mm/aaaa.
        while True:
            start_date = simpledialog.askstring("Nuevo Proyecto", "Ingrese la fecha de inicio (dd/mm/aaaa):")
            try:
                # Intentamos parsear la fecha para validar el formato.
                datetime.strptime(start_date, "%d/%m/%Y")
                break  # La fecha es válida, salimos del ciclo.
            except (ValueError, TypeError):
                messagebox.showerror("Error", "La fecha ingresada no es válida. Asegúrese de usar el formato dd/mm/aaaa.")
        return project_name, start_date

    def update_current_time(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.current_time_label.config(text=now)
        self.after(1000, self.update_current_time)

    def choose_activity(self):
        activity_window = tk.Toplevel(self)
        activity_window.title("Seleccionar actividad")
        activity_window.geometry("300x500")

        ttk.Label(activity_window, text="Seleccione una actividad:", font=("Arial", 12)).pack(pady=10)

        def set_activity(activity):
            self.current_activity = activity
            self.activity_name_label.config(text=f"Actividad Actual: {self.current_activity}", background="yellow")
            activity_window.destroy()
            self.start_activity_timer()

        for activity in self.activities_list:
            ttk.Button(activity_window, text=activity, command=lambda a=activity: set_activity(a)).pack(pady=5)

    def start_activity(self):
        self.choose_activity()

    def start_activity_timer(self):
        if self.current_activity:
            # Solicitar comentarios al iniciar la actividad.
            self.activity_comments = simpledialog.askstring("Comentarios", "Ingrese comentarios para la actividad:")
            self.start_time = datetime.now()
            self.total_paused_time = timedelta()
            self.paused_minutes = 0
            self.paused_time_label.config(text="00:00:00")
            self.start_button.config(state="disabled")
            self.pause_button.config(state="normal", text="Pausar")
            self.stop_button.config(state="normal")
            self.timer_running = True
            self.is_paused = False
            self.notification_shown = False  # Reinicia la notificación
            self.update_elapsed_time()

    def pause_activity(self):
        if not self.is_paused:
            self.pause_time = datetime.now()
            self.pause_button.config(text="Reanudar")
            self.is_paused = True
            self.update_paused_time()
        else:
            self.total_paused_time += datetime.now() - self.pause_time
            paused_time_minutes = (datetime.now() - self.pause_time).seconds // 60
            self.paused_minutes += paused_time_minutes
            self.total_paused_minutes += paused_time_minutes
            self.save_data()
            self.pause_button.config(text="Pausar")
            self.is_paused = False
            # Actualizamos la etiqueta para mostrar el tiempo acumulado en pausa
            self.paused_time_label.config(text=self.format_timedelta(self.total_paused_time))
            self.update_elapsed_time()

    def update_elapsed_time(self):
        if self.timer_running and not self.is_paused:
            elapsed_time = datetime.now() - self.start_time - self.total_paused_time
            self.elapsed_time_label.config(text=str(elapsed_time).split(".")[0])
            # Mostrar notificación si la actividad dura 60 minutos o más.
            if elapsed_time >= timedelta(minutes=60) and not self.notification_shown:
                self.notification_shown = True
                self.show_notification()
            self.after(1000, self.update_elapsed_time)

    def show_notification(self):
        def ring_bell():
            while self.notification_shown:
                self.bell()
                time.sleep(1)  # Ajusta el intervalo de tiempo si es necesario

        threading.Thread(target=ring_bell, daemon=True).start()
        messagebox.showinfo("Notificación", f"La actividad '{self.current_activity}' ha durado 60 minutos o más.")
        self.notification_shown = False

    def update_paused_time(self):
        """
        Actualiza la etiqueta de tiempo en pausa mostrando el tiempo acumulado (más el actual si se está pausado)
        en formato hh:mm:ss.
        """
        if self.is_paused:
            current_pause_duration = datetime.now() - self.pause_time
            total_pause = self.total_paused_time + current_pause_duration
            self.paused_time_label.config(text=self.format_timedelta(total_pause))
            self.after(1000, self.update_paused_time)

    def format_timedelta(self, td):
        """
        Convierte un objeto timedelta en una cadena con formato hh:mm:ss.
        """
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def stop_activity(self):
        end_time = datetime.now()
        active_duration = end_time - self.start_time - self.total_paused_time
        active_minutes = int(active_duration.total_seconds() // 60)
        paused_minutes = int(self.total_paused_time.total_seconds() // 60)

        if self.current_activity:
            self.activities[self.current_activity] = self.activities.get(self.current_activity, 0) + active_minutes

            log_entry = {
                "fecha_inicio": self.formatear_fecha(self.start_time),
                "hora_inicio": self.start_time.strftime("%H:%M:%S"),
                "hora_fin": end_time.strftime("%H:%M:%S"),
                "tiempo_en_pausa_min": paused_minutes,
                "tiempo_no_pausado_min": active_minutes,
                "actividad": self.current_activity,
                "comentarios": self.activity_comments
            }
            self.activity_logs.append(log_entry)
            self.data["activity_logs"] = self.activity_logs
            self.save_data()

            if active_minutes >= 60:
                messagebox.showinfo("Notificación", f"La actividad '{self.current_activity}' ha durado 60 minutos o más.")
                self.bell()

        self.start_button.config(state="normal")
        self.pause_button.config(state="disabled", text="Pausar")
        self.stop_button.config(state="disabled")
        self.timer_running = False
        self.elapsed_time_label.config(text="00:00:00")
        self.paused_time_label.config(text="00:00:00")
        self.activity_name_label.config(text="")
        self.show_statistics()

    def load_data(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        if 'activities' not in data:
            data['activities'] = {}
        if 'total_paused_minutes' not in data:
            data['total_paused_minutes'] = 0
        if 'activity_logs' not in data:
            data['activity_logs'] = []
        return data

    def save_data(self):
        with open(self.filename, "w", encoding="utf-8") as file:
            data = {
                'project_name': self.project_name,
                'start_date': self.start_date,
                'activities': self.activities,
                'total_paused_minutes': self.total_paused_minutes,
                'activity_logs': self.activity_logs
            }
            json.dump(data, file, indent=4, ensure_ascii=False)

    def show_statistics(self):
        # Esta función muestra las gráficas en pantalla (para uso interactivo)
        activities = [activity for activity in self.activities_list]
        minutes = [self.activities.get(activity, 0) for activity in activities]
        total_minutes = sum(minutes)
        total_time_effective = f"{int(total_minutes)} minutos"
        total_paused_time_str = f"{self.total_paused_minutes} minutos en pausa"

        if total_minutes > 0:
            percentages = [f"{(m / total_minutes) * 100:.2f}%" for m in minutes]
        else:
            percentages = ["0.00%" for _ in activities]

        # Valores para la gráfica de pastel
        effective_time = total_minutes
        paused_time = self.total_paused_minutes

        # Validación para la gráfica de pastel:
        if effective_time + paused_time == 0:
            messagebox.showwarning("Advertencia", "No se puede mostrar la gráfica de pastel debido a que no hay datos suficientes.")
            # Mostrar solo la gráfica de barras:
            fig, ax = plt.subplots(figsize=(7, 5))
            bars = ax.bar(activities, minutes, color='blue')
            ax.set_xlabel('Actividad')
            ax.set_ylabel('Minutos')
            ax.set_title(f'Tiempo empleado en actividades\nTiempo total efectivo: {total_time_effective}\n{total_paused_time_str}')
            ax.set_xticklabels(activities, rotation=45)
            for bar, m, percentage in zip(bars, minutes, percentages):
                yval = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, yval, f"{m} min\n{percentage}", ha='center', va='bottom', fontsize=10)
            plt.tight_layout()
            plt.show()
            return

        # Si hay datos suficientes, se muestran ambas gráficas (barras y pastel)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Gráfica de barras:
        bars = ax1.bar(activities, minutes, color='blue')
        ax1.set_xlabel('Actividad')
        ax1.set_ylabel('Minutos')
        ax1.set_title(f'Tiempo empleado en actividades\nTiempo total efectivo: {total_time_effective}\n{total_paused_time_str}')
        ax1.set_xticklabels(activities, rotation=45)
        for bar, m, percentage in zip(bars, minutes, percentages):
            yval = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2, yval, f"{m} min\n{percentage}", ha='center', va='bottom', fontsize=10)

        # Gráfica de pastel:
        def make_autopct(values):
            def my_autopct(pct):
                total = sum(values)
                val = int(round(pct * total / 100.0))
                return f'{pct:.1f}%\n({val} min)'
            return my_autopct

        ax2.pie(
            [effective_time, paused_time],
            labels=["Tiempo Efectivo", "Tiempo en Pausa"],
            autopct=make_autopct([effective_time, paused_time]),
            colors=['green', 'red'],
            startangle=90
        )
        ax2.set_title("Comparación: Tiempo Efectivo vs en Pausa")
        plt.tight_layout()
        plt.show()

    def generate_bar_chart_image(self, filename):
        """Genera la imagen de la gráfica de barras y la guarda en 'filename'."""
        activities = [activity for activity in self.activities_list]
        minutes = [self.activities.get(activity, 0) for activity in activities]
        total_minutes = sum(minutes)
        total_time_effective = f"{int(total_minutes)} minutos"
        total_paused_time_str = f"{self.total_paused_minutes} minutos en pausa"

        plt.figure(figsize=(10, 5))
        bars = plt.bar(activities, minutes, color='blue')
        plt.xlabel('Actividad')
        plt.ylabel('Minutos')
        plt.title(f'Tiempo empleado en actividades\nTiempo total efectivo: {total_time_effective}\n{total_paused_time_str}')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

    def generate_pie_chart_image(self, filename):
        """Genera la imagen de la gráfica de pastel y la guarda en 'filename'."""
        activities = [activity for activity in self.activities_list]
        minutes = [self.activities.get(activity, 0) for activity in activities]
        total_minutes = sum(minutes)
        effective_time = total_minutes
        paused_time = self.total_paused_minutes

        def make_autopct(values):
            def my_autopct(pct):
                total = sum(values)
                val = int(round(pct * total / 100.0))
                return f'{pct:.1f}%\n({val} min)'
            return my_autopct

        plt.figure(figsize=(10, 5))
        plt.pie(
            [effective_time, paused_time],
            labels=["Tiempo Efectivo", "Tiempo en Pausa"],
            autopct=make_autopct([effective_time, paused_time]),
            colors=['green', 'red'],
            startangle=90
        )
        plt.title("Comparación: Tiempo Efectivo vs en Pausa")
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

    def produce_pdf(self):
        # Solicitar el nombre del archivo PDF
        pdf_file = filedialog.asksaveasfilename(
            title="Guardar PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not pdf_file:
            return

        # Configurar el documento en orientación horizontal con márgenes de 2 cm
        doc = SimpleDocTemplate(
            pdf_file,
            pagesize=landscape(letter),
            title="Reporte de Actividades",
            author="Registro de Tiempo",
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm
        )

        styles = getSampleStyleSheet()
        body_style = styles["BodyText"]

        # Función para dibujar el encabezado en cada página
        def header(canvas, doc):
            canvas.saveState()
            project_text = f"Proyecto: {self.project_name}"
            fecha_inicio_dt = datetime.strptime(self.start_date, '%d/%m/%Y')
            date_text = (
                f"Fecha de inicio: {self.formatear_fecha(fecha_inicio_dt)}    "
                f"Fecha de generación: {self.formatear_fecha(datetime.now())}"
            )
            canvas.setFont('Helvetica-Bold', 10)
            width, height = doc.pagesize
            canvas.drawCentredString(width / 2.0, height - 40, project_text)
            canvas.drawCentredString(width / 2.0, height - 55, date_text)
            canvas.restoreState()

        Story = []

        # --- Primera Página: Gráfica de Barras ---
        bar_chart_file = "temp_bar_chart.png"
        self.generate_bar_chart_image(bar_chart_file)
        im_bar = Image(bar_chart_file)
        available_width = doc.width
        available_height = doc.height
        aspect_ratio = im_bar.imageWidth / im_bar.imageHeight
        if available_width / aspect_ratio <= available_height:
            im_bar.drawWidth = available_width
            im_bar.drawHeight = available_width / aspect_ratio
        else:
            im_bar.drawHeight = available_height
            im_bar.drawWidth = available_height * aspect_ratio
        im_bar.hAlign = 'CENTER'
        Story.append(im_bar)

        # Salto de página para la gráfica de pastel o mensaje
        Story.append(PageBreak())

        # --- Segunda Página: Gráfica de Pastel o Mensaje ---
        # Se calculan los tiempos:
        activities = [activity for activity in self.activities_list]
        minutes = [self.activities.get(activity, 0) for activity in activities]
        total_minutes = sum(minutes)
        effective_time = total_minutes
        paused_time = self.total_paused_minutes

        if effective_time + paused_time == 0:
            # No hay datos suficientes para la gráfica de pastel
            Story.append(Paragraph("No se puede mostrar la gráfica de pastel debido a que no hay datos suficientes.", body_style))
        else:
            pie_chart_file = "temp_pie_chart.png"
            self.generate_pie_chart_image(pie_chart_file)
            im_pie = Image(pie_chart_file)
            aspect_ratio = im_pie.imageWidth / im_pie.imageHeight
            if available_width / aspect_ratio <= available_height:
                im_pie.drawWidth = available_width
                im_pie.drawHeight = available_width / aspect_ratio
            else:
                im_pie.drawHeight = available_height
                im_pie.drawWidth = available_height * aspect_ratio
            im_pie.hAlign = 'CENTER'
            Story.append(im_pie)

        # Salto de página para que la tabla inicie en la siguiente página
        Story.append(PageBreak())

        # --- Tercera Página en Adelante: Tabla de Registros ---
        headers = ["Fecha", "Inicio", "Fin", "Interrupción (min)", "A Tiempo(min)", "Actividad", "Comentarios"]
        table_data = [headers]
        for log in self.activity_logs:
            row = [
                Paragraph(log.get("fecha_inicio", ""), body_style),
                Paragraph(log.get("hora_inicio", ""), body_style),
                Paragraph(log.get("hora_fin", ""), body_style),
                Paragraph(str(log.get("tiempo_en_pausa_min", "")), body_style),
                Paragraph(str(log.get("tiempo_no_pausado_min", "")), body_style),
                Paragraph(log.get("actividad", ""), body_style),
                Paragraph(log.get("comentarios", ""), body_style)
            ]
            table_data.append(row)

        total_width = doc.width
        num_columns = len(headers)
        col_widths = [total_width / num_columns] * num_columns

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        Story.append(t)

        doc.build(Story, onFirstPage=header, onLaterPages=header)
        messagebox.showinfo("PDF Generado", "El PDF ha sido generado exitosamente.")

    def show_table(self):
        """Abre una nueva ventana que muestra los registros en una tabla."""
        table_window = tk.Toplevel(self)
        table_window.title("Registro de Actividades")
        table_window.geometry("1000x400")

        # Definición de columnas para el Treeview
        columns = ("fecha", "inicio", "fin", "interrupcion", "tiempo", "actividad", "comentarios")
        tree = ttk.Treeview(table_window, columns=columns, show="headings")

        # Configuración de los encabezados de las columnas
        tree.heading("fecha", text="Fecha")
        tree.heading("inicio", text="Inicio")
        tree.heading("fin", text="Fin")
        tree.heading("interrupcion", text="Interrupción (min)")
        tree.heading("tiempo", text="A Tiempo (min)")
        tree.heading("actividad", text="Actividad")
        tree.heading("comentarios", text="Comentarios")

        # Opcional: definir el ancho y la alineación de las columnas
        tree.column("fecha", width=100, anchor="center")
        tree.column("inicio", width=100, anchor="center")
        tree.column("fin", width=100, anchor="center")
        tree.column("interrupcion", width=120, anchor="center")
        tree.column("tiempo", width=120, anchor="center")
        tree.column("actividad", width=120, anchor="center")
        tree.column("comentarios", width=300, anchor="center")

        # Insertar los datos de cada registro en el Treeview
        for log in self.activity_logs:
            tree.insert("", "end", values=(
                log.get("fecha_inicio", ""),
                log.get("hora_inicio", ""),
                log.get("hora_fin", ""),
                log.get("tiempo_en_pausa_min", ""),
                log.get("tiempo_no_pausado_min", ""),
                log.get("actividad", ""),
                log.get("comentarios", "")
            ))

        tree.pack(fill="both", expand=True)

        # Agregar una barra de desplazamiento vertical
        scrollbar = ttk.Scrollbar(table_window, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def change_project(self):
        """Permite al usuario cambiar de proyecto (abrir uno existente o crear uno nuevo)."""
        # Evitar cambiar de proyecto durante una actividad en curso
        if self.timer_running:
            messagebox.showwarning("Advertencia", "No se puede cambiar de proyecto mientras se registra una actividad.")
            return

        respuesta = messagebox.askyesno("Cambiar Proyecto", 
                                        "¿Desea abrir un proyecto existente?\n(Sí: Abrir | No: Crear uno nuevo)")
        if respuesta:
            new_file = filedialog.askopenfilename(title="Seleccione un archivo de datos", filetypes=[("Text files", "*.txt")])
            if not new_file:
                return
        else:
            new_file = filedialog.asksaveasfilename(title="Crear un nuevo archivo de datos", 
                                                     defaultextension=".txt", 
                                                     filetypes=[("Text files", "*.txt")])
            if not new_file:
                return

        # Actualizar la ruta del archivo y recargar los datos
        self.filename = new_file
        self.data = self.load_data()
        self.activities = self.data.get('activities', {})
        self.total_paused_minutes = self.data.get('total_paused_minutes', 0)
        self.activity_logs = self.data.get('activity_logs', [])
        self.project_name = self.data.get('project_name', None)
        self.start_date = self.data.get('start_date', None)
        if not self.project_name:
            self.project_name, self.start_date = self.get_project_details()
            self.data['project_name'] = self.project_name
            self.data['start_date'] = self.start_date
            self.save_data()
        self.project_label.config(text=f"Proyecto: {self.project_name}")
        messagebox.showinfo("Proyecto Actualizado", f"Se ha cargado el proyecto: {self.project_name}")

if __name__ == "__main__":
    app = RegistroTiempo()
    app.mainloop()
