"""
Analytics Page - Usage statistics and insights
"""
import streamlit as st
from pathlib import Path
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import DatabaseManager
from database.vector_store import VectorStore
from utils.export import ExportManager

# Page config
st.set_page_config(
    page_title="Analytics - Legal Document Assistant",
    page_icon="📊",
    layout="wide"
)


def render_metric_card(label, value, delta=None, delta_color="normal"):
    """Render a styled metric card"""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def main():
    # Check authentication
    if not st.session_state.get('authenticated', False):
        st.warning("Please login to access analytics.")
        st.stop()

    user = st.session_state.user

    st.markdown("# 📊 Analytics Dashboard")
    st.markdown("View usage statistics and insights for your legal document assistant.")

    # Time period selector
    col1, col2 = st.columns([3, 1])
    with col2:
        time_period = st.selectbox(
            "Time Period",
            options=[7, 14, 30, 90],
            format_func=lambda x: f"Last {x} days",
            index=2
        )

    st.divider()

    # Get analytics data
    analytics = DatabaseManager.get_analytics_summary(days=time_period)

    # Summary metrics
    st.markdown("### 📈 Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px; border-radius: 12px; color: white; text-align: center;">
            <h3 style="margin: 0; font-size: 2em;">{}</h3>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">Total Queries</p>
        </div>
        """.format(analytics.get('total_queries', 0)), unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                    padding: 20px; border-radius: 12px; color: white; text-align: center;">
            <h3 style="margin: 0; font-size: 2em;">{}</h3>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">Active Users</p>
        </div>
        """.format(analytics.get('active_users', 0)), unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
                    padding: 20px; border-radius: 12px; color: white; text-align: center;">
            <h3 style="margin: 0; font-size: 2em;">{}</h3>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">Documents</p>
        </div>
        """.format(analytics.get('total_documents', 0)), unsafe_allow_html=True)

    with col4:
        avg_time = analytics.get('avg_response_time_ms', 0)
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4776E6 0%, #8E54E9 100%);
                    padding: 20px; border-radius: 12px; color: white; text-align: center;">
            <h3 style="margin: 0; font-size: 2em;">{:.0f}ms</h3>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">Avg Response Time</p>
        </div>
        """.format(avg_time), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📈 Queries Over Time")

        queries_by_day = analytics.get('queries_by_day', [])

        if queries_by_day:
            import pandas as pd

            df = pd.DataFrame(queries_by_day)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')

            st.line_chart(df['count'], use_container_width=True)
        else:
            st.info("No query data available for the selected period.")

    with col2:
        st.markdown("### 📊 Document Statistics")

        processed = analytics.get('processed_documents', 0)
        total_docs = analytics.get('total_documents', 0)
        unprocessed = total_docs - processed

        if total_docs > 0:
            import pandas as pd

            doc_data = pd.DataFrame({
                'Status': ['Processed', 'Pending'],
                'Count': [processed, unprocessed]
            })

            st.bar_chart(doc_data.set_index('Status'), use_container_width=True)
        else:
            st.info("No documents uploaded yet.")

    st.divider()

    # Detailed metrics
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔥 Popular Queries")

        popular = DatabaseManager.get_popular_queries(limit=10)

        if popular:
            for i, item in enumerate(popular, 1):
                query = item['query'][:50] + "..." if len(item['query']) > 50 else item['query']
                count = item['count']

                st.markdown(f"**{i}.** {query}")
                st.progress(count / popular[0]['count'] if popular[0]['count'] > 0 else 0)
                st.caption(f"{count} queries")
        else:
            st.info("No queries recorded yet.")

    with col2:
        st.markdown("### 💾 System Statistics")

        # Vector store stats
        try:
            vs = VectorStore()
            vs_stats = vs.get_collection_stats()

            st.metric("Total Chunks in Vector Store", vs_stats.get('total_chunks', 0))
            st.metric("Unique Documents Indexed", vs_stats.get('unique_documents', 0))
        except Exception as e:
            st.warning(f"Could not load vector store stats: {e}")

        # Token usage
        total_tokens = analytics.get('total_tokens_used', 0)
        st.metric("Total Tokens Used", f"{total_tokens:,}")

        # Estimated cost (approximate)
        estimated_cost = (total_tokens / 1000) * 0.002  # Approximate cost
        st.metric("Estimated API Cost", f"${estimated_cost:.2f}")

    st.divider()

    # User statistics (Admin only)
    if user.get('role') in ['admin', 'superadmin']:
        st.markdown("### 👥 User Statistics")

        all_users = DatabaseManager.get_all_users()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Users", len(all_users))

        with col2:
            active_users = sum(1 for u in all_users if u.is_active)
            st.metric("Active Users", active_users)

        with col3:
            verified_users = sum(1 for u in all_users if u.is_verified)
            st.metric("Verified Users", verified_users)

        # User list
        st.markdown("#### Recent Users")

        users_sorted = sorted(all_users, key=lambda x: x.created_at, reverse=True)[:10]

        for user_item in users_sorted:
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

            with col1:
                st.text(user_item.username)

            with col2:
                st.caption(user_item.email)

            with col3:
                st.caption(user_item.role.value)

            with col4:
                status = "🟢" if user_item.is_active else "🔴"
                st.caption(status)

    st.divider()

    # Export section
    st.markdown("### 📥 Export Analytics")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Export Report (Markdown)", use_container_width=True):
            exporter = ExportManager()
            report = exporter.export_analytics_report(
                analytics,
                title=f"Analytics Report - Last {time_period} days"
            )

            st.download_button(
                label="Download Report",
                data=report,
                file_name=f"analytics_report_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )

    with col2:
        if st.button("📊 Export Data (JSON)", use_container_width=True):
            import json

            data = {
                'generated_at': datetime.now().isoformat(),
                'time_period_days': time_period,
                'summary': analytics,
                'popular_queries': DatabaseManager.get_popular_queries(limit=20)
            }

            st.download_button(
                label="Download JSON",
                data=json.dumps(data, indent=2, default=str),
                file_name=f"analytics_data_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )


if __name__ == "__main__":
    main()
