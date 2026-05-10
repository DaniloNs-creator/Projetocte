import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

class AppMasterSaf:
    def __init__(self, root):
        self.root = root
        self.root.title("MasterSAF - Automação de Download XML")
        self.root.geometry("600x650")
        self.root.configure(padx=20, pady=20)
        self.root.resizable(False, False)

        # Configurando o estilo visual (Tema moderno do ttk)
        self.style = ttk.Style()
        self.style.theme_use('clam') # 'clam', 'alt', 'default', ou 'classic'
        
        # Estilos customizados
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        self.style.configure("TLabelframe", background="#f0f0f0", font=("Segoe UI", 11, "bold"))
        self.style.configure("TLabelframe.Label", background="#f0f0f0", foreground="#333333")
        
        self.root.configure(bg="#f0f0f0")

        self.criar_widgets()

    def criar_widgets(self):
        # --- FRAME DE CREDENCIAIS ---
        frame_login = ttk.LabelFrame(self.root, text=" 1. Credenciais de Acesso ")
        frame_login.pack(fill="x", pady=(0, 15), ipady=5)

        ttk.Label(frame_login, text="Login:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_usuario = ttk.Entry(frame_login, width=30)
        self.entry_usuario.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        ttk.Label(frame_login, text="Senha:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.entry_senha = ttk.Entry(frame_login, width=20, show="*")
        self.entry_senha.grid(row=0, column=3, padx=10, pady=10, sticky="w")

        # --- FRAME DE CONFIGURAÇÕES DE PESQUISA ---
        frame_config = ttk.LabelFrame(self.root, text=" 2. Configurações da Pesquisa e Loop ")
        frame_config.pack(fill="x", pady=(0, 15), ipady=5)

        ttk.Label(frame_config, text="Data Inicial:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_dt_ini = ttk.Entry(frame_config, width=15)
        self.entry_dt_ini.insert(0, "08/05/2026")
        self.entry_dt_ini.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        ttk.Label(frame_config, text="Data Final:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.entry_dt_fin = ttk.Entry(frame_config, width=15)
        self.entry_dt_fin.insert(0, "08/05/2026")
        self.entry_dt_fin.grid(row=0, column=3, padx=10, pady=10, sticky="w")

        ttk.Label(frame_config, text="Qtd. de Loops (Páginas):").grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        self.entry_loops = ttk.Entry(frame_config, width=10)
        self.entry_loops.insert(0, "5") # Valor padrão
        self.entry_loops.grid(row=1, column=2, padx=10, pady=10, sticky="w")

        # --- BOTÃO DE INICIAR ---
        self.btn_iniciar = ttk.Button(self.root, text="🚀 INICIAR AUTOMAÇÃO", command=self.iniciar_thread)
        self.btn_iniciar.pack(fill="x", pady=(0, 15), ipady=5)

        # --- FRAME DE LOGS (Terminal visual) ---
        frame_log = ttk.LabelFrame(self.root, text=" Painel de Atividades ")
        frame_log.pack(fill="both", expand=True)

        self.log_text = scrolledtext.ScrolledText(frame_log, wrap=tk.WORD, width=60, height=10, font=("Consolas", 9), bg="#1e1e1e", fg="#00ff00")
        self.log_text.pack(padx=10, pady=10, fill="both", expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        self.inserir_log("Aplicativo iniciado. Aguardando comando...")

    def inserir_log(self, mensagem):
        """Função para inserir texto no painel de atividades"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"> {mensagem}\n")
        self.log_text.see(tk.END) # Rola automaticamente para o final
        self.log_text.config(state=tk.DISABLED)

    def iniciar_thread(self):
        """Inicia a automação em uma thread separada para não travar a interface"""
        # Validação básica
        if not self.entry_usuario.get() or not self.entry_senha.get():
            messagebox.showwarning("Aviso", "Por favor, preencha Login e Senha!")
            return
        
        try:
            int(self.entry_loops.get())
        except ValueError:
            messagebox.showerror("Erro", "A quantidade de loops deve ser um número inteiro!")
            return

        self.btn_iniciar.config(state=tk.DISABLED) # Desabilita o botão para evitar múltiplos cliques
        self.inserir_log("--- Nova execução iniciada ---")
        
        # Cria e inicia a Thread
        thread = threading.Thread(target=self.rodar_automacao)
        thread.daemon = True
        thread.start()

    def rodar_automacao(self):
        usuario = self.entry_usuario.get()
        senha = self.entry_senha.get()
        dt_ini = self.entry_dt_ini.get()
        dt_fin = self.entry_dt_fin.get()
        loops = int(self.entry_loops.get())

        self.inserir_log("Abrindo o navegador Google Chrome...")
        driver = None

        try:
            driver = webdriver.Chrome()
            driver.maximize_window()
            
            self.inserir_log("Acessando a página de login...")
            driver.get("https://p.dfe.mastersaf.com.br/mvc/login")
            time.sleep(2)
            
            self.inserir_log("Realizando Login...")
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').click()
            driver.find_element(By.XPATH, '//*[@id="nomeusuario"]').send_keys(usuario)
            
            driver.find_element(By.XPATH, '//*[@id="senha"]').click()
            driver.find_element(By.XPATH, '//*[@id="senha"]').send_keys(senha)
            
            driver.find_element(By.XPATH, '//*[@id="enter"]').click()
            time.sleep(3)
            
            self.inserir_log("Acessando Listagem Receptor CTEs...")
            driver.find_element(By.XPATH, '//*[@id="linkListagemReceptorCTEs"]/a').click()
            time.sleep(3)
            
            self.inserir_log(f"Inserindo datas: {dt_ini} a {dt_fin}")
            campo_dt_inicial = driver.find_element(By.XPATH, '//*[@id="consultaDataInicial"]')
            campo_dt_inicial.click()
            campo_dt_inicial.send_keys(Keys.CONTROL, 'a')
            campo_dt_inicial.send_keys(dt_ini)
            
            campo_dt_final = driver.find_element(By.XPATH, '//*[@id="consultaDataFinal"]')
            campo_dt_final.click()
            campo_dt_final.send_keys(Keys.CONTROL, 'a')
            campo_dt_final.send_keys(dt_fin)
            time.sleep(3)
            
            self.inserir_log("Atualizando listagem...")
            driver.find_element(By.XPATH, '//*[@id="listagem_atualiza"]').click()
            time.sleep(3)
            
            self.inserir_log("Selecionando opção 5 na tabela...")
            driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select').click()
            time.sleep(1)
            driver.find_element(By.XPATH, '//*[@id="plistagem_center"]/table/tbody/tr/td[8]/select/option[5]').click()
            time.sleep(3)
            
            self.inserir_log(f"Iniciando loop de download ({loops} vezes)...")
            for i in range(loops):
                self.inserir_log(f"Processando página {i + 1} de {loops}...")
                
                driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input').click()
                time.sleep(3)
                
                driver.find_element(By.XPATH, '//*[@id="xml_multiplos"]/h3').click()
                time.sleep(3)
                
                driver.find_element(By.XPATH, '//*[@id="downloadEmMassaXml"]').click()
                time.sleep(2)
                
                driver.find_element(By.XPATH, '//*[@id="jqgh_listagem_checkBox"]/div/input').click()
                time.sleep(1)
                
                self.inserir_log(f"Avançando para a próxima página...")
                driver.find_element(By.XPATH, '//*[@id="next_plistagem"]/span').click()
                time.sleep(4)
                
            self.inserir_log("🎉 Automação concluída com sucesso!")
            messagebox.showinfo("Sucesso", "Todos os downloads foram concluídos!")
            
        except Exception as e:
            self.inserir_log(f"❌ ERRO: {str(e)}")
            messagebox.showerror("Erro na Automação", f"Ocorreu um erro:\n{str(e)}")
            
        finally:
            self.inserir_log("Fechando o navegador...")
            if driver:
                driver.quit()
            # Reabilita o botão para permitir rodar novamente
            self.btn_iniciar.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = AppMasterSaf(root)
    root.mainloop()
