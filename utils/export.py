"""
Export Manager
Handles exporting chat history and data
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])

from config import EXPORTS_DIR


class ExportManager:
    """Manages data exports"""

    def __init__(self, export_dir: Optional[str] = None):
        self.export_dir = Path(export_dir or EXPORTS_DIR)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_chat_to_text(
        self,
        messages: List[Dict[str, Any]],
        session_title: str = "Chat Export",
        include_sources: bool = True
    ) -> str:
        """Export chat messages to plain text format"""
        lines = [
            f"Chat Export: {session_title}",
            f"Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            ""
        ]

        for msg in messages:
            role = "User" if msg.get('role') == 'user' else "Assistant"
            content = msg.get('content', '')
            timestamp = msg.get('created_at', '')

            lines.append(f"[{role}] ({timestamp})")
            lines.append(content)

            if include_sources and msg.get('sources'):
                lines.append("\nSources:")
                for source in msg['sources']:
                    location = source.get('location', 'Document')
                    similarity = source.get('similarity', 0)
                    lines.append(f"  - {location} (Relevance: {similarity:.0%})")

            lines.append("")
            lines.append("-" * 40)
            lines.append("")

        return "\n".join(lines)

    def export_chat_to_markdown(
        self,
        messages: List[Dict[str, Any]],
        session_title: str = "Chat Export",
        include_sources: bool = True
    ) -> str:
        """Export chat messages to Markdown format"""
        lines = [
            f"# {session_title}",
            f"*Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "---",
            ""
        ]

        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            timestamp = msg.get('created_at', '')

            if role == 'user':
                lines.append(f"## 👤 User")
            else:
                lines.append(f"## 🤖 Assistant")

            if timestamp:
                lines.append(f"*{timestamp}*")
            lines.append("")
            lines.append(content)
            lines.append("")

            if include_sources and msg.get('sources'):
                lines.append("### Sources")
                for i, source in enumerate(msg['sources'], 1):
                    location = source.get('location', 'Document')
                    similarity = source.get('similarity', 0)
                    preview = source.get('content_preview', '')[:100]
                    lines.append(f"{i}. **{location}** (Relevance: {similarity:.0%})")
                    if preview:
                        lines.append(f"   > {preview}...")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def export_chat_to_json(
        self,
        messages: List[Dict[str, Any]],
        session_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Export chat messages to JSON format"""
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'session': session_info or {},
            'messages': messages
        }

        return json.dumps(export_data, indent=2, default=str)

    def export_chat_to_html(
        self,
        messages: List[Dict[str, Any]],
        session_title: str = "Chat Export",
        include_sources: bool = True
    ) -> str:
        """Export chat messages to HTML format"""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{session_title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .message {{
            margin: 15px 0;
            padding: 15px;
            border-radius: 10px;
            background: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .user {{
            border-left: 4px solid #667eea;
        }}
        .assistant {{
            border-left: 4px solid #28a745;
        }}
        .role {{
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }}
        .content {{
            line-height: 1.6;
            white-space: pre-wrap;
        }}
        .sources {{
            margin-top: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            font-size: 0.9em;
        }}
        .source-item {{
            margin: 5px 0;
            color: #666;
        }}
        .timestamp {{
            font-size: 0.8em;
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{session_title}</h1>
        <p>Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""

        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '').replace('\n', '<br>')
            timestamp = msg.get('created_at', '')

            role_display = "👤 User" if role == 'user' else "🤖 Assistant"

            html += f"""
    <div class="message {role}">
        <div class="role">{role_display}</div>
        <div class="timestamp">{timestamp}</div>
        <div class="content">{content}</div>
"""

            if include_sources and msg.get('sources'):
                html += '        <div class="sources"><strong>Sources:</strong>'
                for source in msg['sources']:
                    location = source.get('location', 'Document')
                    similarity = source.get('similarity', 0)
                    html += f'<div class="source-item">📚 {location} (Relevance: {similarity:.0%})</div>'
                html += '</div>'

            html += '    </div>'

        html += """
</body>
</html>"""

        return html

    def save_export(
        self,
        content: str,
        filename: str,
        format_type: str = "txt"
    ) -> str:
        """Save export content to file and return path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        full_filename = f"{safe_filename}_{timestamp}.{format_type}"

        file_path = self.export_dir / full_filename

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(file_path)

    def export_analytics_report(
        self,
        analytics_data: Dict[str, Any],
        title: str = "Analytics Report"
    ) -> str:
        """Export analytics data to markdown report"""
        lines = [
            f"# {title}",
            f"*Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## Summary Statistics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Queries | {analytics_data.get('total_queries', 0)} |",
            f"| Total Users | {analytics_data.get('total_users', 0)} |",
            f"| Active Users | {analytics_data.get('active_users', 0)} |",
            f"| Total Documents | {analytics_data.get('total_documents', 0)} |",
            f"| Processed Documents | {analytics_data.get('processed_documents', 0)} |",
            f"| Avg Response Time | {analytics_data.get('avg_response_time_ms', 0):.0f}ms |",
            f"| Total Tokens Used | {analytics_data.get('total_tokens_used', 0):,} |",
            "",
        ]

        # Queries by day
        if analytics_data.get('queries_by_day'):
            lines.extend([
                "## Queries by Day",
                "",
                "| Date | Count |",
                "|------|-------|",
            ])
            for day_data in analytics_data['queries_by_day']:
                lines.append(f"| {day_data['date']} | {day_data['count']} |")
            lines.append("")

        return "\n".join(lines)
