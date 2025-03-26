import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import threading
import subprocess
import json
import shutil

def find_ffmpeg_executable(name):
    """Find FFmpeg executable by trying common paths and PATH"""
    path = shutil.which(name)
    if path:
        return path
    
    common_locations = [
        os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'FFmpeg', 'bin', f'{name}.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'FFmpeg', 'bin', f'{name}.exe'),
        f'C:\\ffmpeg\\bin\\{name}.exe',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg', 'bin', f'{name}.exe'),
    ]
    
    for location in common_locations:
        if os.path.isfile(location):
            return location
    
    return name

FFMPEG_PATH = find_ffmpeg_executable('ffmpeg')
FFPROBE_PATH = find_ffmpeg_executable('ffprobe')

QUALITY_PRESETS = {
    "High (Large File)": 18,
    "Medium-High": 21,
    "Medium (Balanced)": 23,
    "Medium-Low": 26,
    "Low (Small File)": 28
}

class VideoConverter(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("H.265 to H.264 Converter")
        self.geometry("600x400")
        self.minsize(500, 350)
        
        self.files_to_convert = []
        self.output_directory = os.path.expanduser("~/Videos")
        self.quality_preset = "Medium (Balanced)"
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        list_frame = ttk.LabelFrame(main_frame, text="Files to convert")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.file_listbox.yview)
        
        options_frame = ttk.LabelFrame(main_frame, text="Conversion Options")
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(options_frame, text="Quality:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.quality_var = tk.StringVar(value=self.quality_preset)
        quality_combo = ttk.Combobox(options_frame, textvariable=self.quality_var, state="readonly")
        quality_combo['values'] = list(QUALITY_PRESETS.keys())
        quality_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(options_frame, text="Higher quality = larger file size").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.output_dir_var = tk.StringVar(value=f"Output: {self.output_directory}")
        
        output_dir_btn = ttk.Button(button_frame, text="Select Output Directory", command=self.select_output_dir)
        output_dir_btn.pack(side=tk.LEFT, padx=5)
        
        output_dir_label = ttk.Label(button_frame, textvariable=self.output_dir_var, wraplength=250)
        output_dir_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        convert_btn = ttk.Button(button_frame, text="Convert", command=self.start_conversion)
        convert_btn.pack(side=tk.RIGHT, padx=5)
        
        clear_btn = ttk.Button(button_frame, text="Clear List", command=self.clear_list)
        clear_btn.pack(side=tk.RIGHT, padx=5)
        
        browse_btn = ttk.Button(button_frame, text="Browse Files", command=self.browse_files)
        browse_btn.pack(side=tk.RIGHT, padx=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.pack(anchor=tk.W)
        
    def browse_files(self):
        filetypes = [
            ("Video files", "*.mp4 *.mkv *.avi *.mov *.flv *.webm"),
            ("All files", "*.*")
        ]
        files = filedialog.askopenfilenames(
            title="Select video files to convert",
            filetypes=filetypes
        )
        if files:
            self.process_files(files)
    
    def is_video_file(self, file_path):
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm']
        _, ext = os.path.splitext(file_path)
        return ext.lower() in video_extensions
    
    def is_h264_video(self, file_path):
        try:
            cmd = [
                FFPROBE_PATH, 
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name',
                '-of', 'json',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            
            if 'streams' in data and data['streams']:
                codec = data['streams'][0].get('codec_name', '').lower()
                return codec in ['h264', 'avc1']
                
        except Exception as e:
            print(f"Error checking codec: {str(e)}")
        
        return False
    
    def process_files(self, file_paths):
        if not file_paths:
            return
            
        h264_files = []
        
        for file_path in file_paths:
            if file_path not in self.files_to_convert:
                if self.is_h264_video(file_path):
                    h264_files.append(os.path.basename(file_path))
                    self.file_listbox.insert(tk.END, f"{os.path.basename(file_path)} [Already H.264]")
                else:
                    self.files_to_convert.append(file_path)
                    self.file_listbox.insert(tk.END, os.path.basename(file_path))
        
        if h264_files:
            files_str = ", ".join(h264_files)
            if len(h264_files) == 1:
                messagebox.showinfo("Already H.264", f"The file {files_str} is already in H.264 format. It has been marked in the list.")
            else:
                messagebox.showinfo("Already H.264", f"The following files are already in H.264 format: {files_str}. They have been marked in the list.")
    
    def select_output_dir(self):
        directory = filedialog.askdirectory(initialdir=self.output_directory)
        if directory:
            self.output_directory = directory
            self.output_dir_var.set(f"Output: {self.output_directory}")
    
    def clear_list(self):
        self.files_to_convert = []
        self.file_listbox.delete(0, tk.END)
        self.status_var.set("Ready")
        self.progress_var.set(0)
    
    def start_conversion(self):
        if not self.files_to_convert:
            messagebox.showinfo("No Files", "Please add video files to convert")
            return
        
        threading.Thread(target=self.convert_files, daemon=True).start()
    
    def convert_files(self):
        total_files = len(self.files_to_convert)
        quality_preset = self.quality_var.get()
        crf_value = QUALITY_PRESETS.get(quality_preset, 23)
        
        for i, file_path in enumerate(self.files_to_convert.copy()):
            file_name = os.path.basename(file_path)
            base_name, _ = os.path.splitext(file_name)
            output_path = os.path.join(self.output_directory, f"{base_name}_h264.mp4")
            
            self.status_var.set(f"Converting {i+1}/{total_files}: {file_name}")
            
            try:
                cmd = [
                    FFMPEG_PATH,
                    '-i', file_path,
                    '-c:v', 'libx264',
                    '-crf', str(crf_value),
                    '-profile:v', 'main',
                    '-level', '4.0',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-movflags', '+faststart',
                    '-preset', 'medium',
                    '-y',
                    output_path
                ]
                
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode != 0:
                    raise Exception(f"FFmpeg error: {process.stderr}")
                
                progress = ((i + 1) / total_files) * 100
                self.progress_var.set(progress)
                
            except Exception as e:
                messagebox.showerror("Conversion Error", f"Error converting {file_name}: {str(e)}")
        
        self.status_var.set("Conversion completed")
        messagebox.showinfo("Conversion Complete", f"All files have been converted successfully with {quality_preset} quality")

def main():
    app = VideoConverter()
    app.mainloop()

if __name__ == "__main__":
    main() 