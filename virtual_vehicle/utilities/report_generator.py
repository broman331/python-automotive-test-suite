
import os
import datetime

class ReportGenerator:
    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def generate(self, test_name, bus_log, result="PASS"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = os.path.join(self.output_dir, f"{test_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: sans-serif; padding: 20px; }}
                h1 {{ color: #333; }}
                .pass {{ color: green; }}
                .fail {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .alert {{ background-color: #ffdddd; color: #a94442; }}
            </style>
        </head>
        <body>
            <h1>Test Report: {test_name}</h1>
            <p><strong>Time:</strong> {timestamp}</p>
            <p><strong>Result:</strong> <span class="{result.lower()}">{result}</span></p>
            
            <h2>Message Log</h2>
            <table>
                <tr>
                    <th>Time Step (approx)</th>
                    <th>Sender</th>
                    <th>Message ID</th>
                    <th>Data</th>
                </tr>
        """
        
        for i, msg in enumerate(bus_log):
            row_class = ""
            if "ALERT" in str(msg['id']) or "WARNING" in str(msg['id']):
                row_class = "alert"
            
            data_str = str(msg['data'])
            if len(data_str) > 100:
                data_str = data_str[:100] + "..."

            html += f"""
                <tr class="{row_class}">
                    <td>{i}</td>
                    <td>{msg['sender']}</td>
                    <td>{msg['id']}</td>
                    <td>{data_str}</td>
                </tr>
            """
            
        html += """
            </table>
        </body>
        </html>
        """
        
        with open(filename, "w") as f:
            f.write(html)
        
        print(f"Report generated: {filename}")
