"""
Real-time Progress Tracking Component
"""

import streamlit as st
import time
from datetime import datetime
import threading
from queue import Queue


class PipelineProgressTracker:
    """Real-time progress tracker for the pipeline"""
    
    def __init__(self):
        self.steps = [
            {"name": "Generate BRD", "icon": "📝", "status": "pending", "progress": 0},
            {"name": "Create Jira Stories", "icon": "📋", "status": "pending", "progress": 0},
            {"name": "Generate Code", "icon": "💻", "status": "pending", "progress": 0},
            {"name": "Generate Tests", "icon": "🧪", "status": "pending", "progress": 0},
            {"name": "Validate & Deploy", "icon": "✅", "status": "pending", "progress": 0}
        ]
        self.current_step = 0
        self.overall_progress = 0
        self.logs = []
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start the progress tracker"""
        self.start_time = datetime.now()
        self.logs.append({"time": self.start_time, "level": "INFO", "message": "Pipeline started"})
    
    def update_step(self, step_index: int, status: str, progress: int = 0, message: str = ""):
        """Update a specific step"""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]["status"] = status
            self.steps[step_index]["progress"] = progress
            self.current_step = step_index
            
            if message:
                self.logs.append({
                    "time": datetime.now(),
                    "level": "INFO",
                    "message": message
                })
            
            # Calculate overall progress
            self.overall_progress = (step_index * 20) + (progress / 5)
    
    def complete_step(self, step_index: int, message: str = ""):
        """Mark a step as complete"""
        self.update_step(step_index, "complete", 100, message)
    
    def fail_step(self, step_index: int, error: str):
        """Mark a step as failed"""
        self.update_step(step_index, "failed", 0, "")
        self.logs.append({
            "time": datetime.now(),
            "level": "ERROR",
            "message": error
        })
    
    def finish(self, success: bool = True):
        """Finish the pipeline"""
        self.end_time = datetime.now()
        status = "SUCCESS" if success else "FAILED"
        self.logs.append({
            "time": self.end_time,
            "level": "INFO" if success else "ERROR",
            "message": f"Pipeline {status}"
        })
    
    def get_elapsed_time(self):
        """Get elapsed time"""
        if self.start_time:
            end = self.end_time or datetime.now()
            delta = end - self.start_time
            return f"{delta.total_seconds():.1f}s"
        return "0s"


def render_progress_tracker(tracker: PipelineProgressTracker):
    """Render the progress tracker UI"""
    
    st.markdown("### ⚡ Pipeline Progress")
    
    # Overall progress bar
    st.progress(tracker.overall_progress / 100, text=f"Overall Progress: {tracker.overall_progress:.0f}%")
    
    # Time elapsed
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Elapsed Time:** {tracker.get_elapsed_time()}")
    with col2:
        if tracker.end_time:
            st.markdown("**Status:** ✅ Complete" if tracker.steps[-1]["status"] == "complete" else "**Status:** ❌ Failed")
        else:
            st.markdown("**Status:** 🔄 Running")
    
    st.markdown("---")
    
    # Individual steps
    st.markdown("**Pipeline Steps:**")
    
    for i, step in enumerate(tracker.steps):
        render_step_card(i, step, is_current=(i == tracker.current_step))
    
    # Logs viewer
    st.markdown("---")
    with st.expander("📜 View Logs", expanded=False):
        render_logs(tracker.logs)


def render_step_card(index: int, step: dict, is_current: bool = False):
    """Render a single step card"""
    
    status = step["status"]
    icon = step["icon"]
    name = step["name"]
    progress = step["progress"]
    
    # Status styling
    if status == "complete":
        status_icon = "✅"
        bg_color = "#d4edda"
        border_color = "#28a745"
    elif status == "failed":
        status_icon = "❌"
        bg_color = "#f8d7da"
        border_color = "#dc3545"
    elif is_current and status == "running":
        status_icon = "🔄"
        bg_color = "#fff3cd"
        border_color = "#ffc107"
    else:
        status_icon = "⏳"
        bg_color = "#e7f3ff"
        border_color = "#6c757d"
    
    # Render card
    with st.container():
        col1, col2, col3 = st.columns([1, 4, 1])
        
        with col1:
            st.markdown(f"<h2 style='margin:0;'>{icon}</h2>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"**Step {index + 1}: {name}**")
            if status == "running" or (is_current and status == "pending"):
                st.progress(progress / 100)
        
        with col3:
            st.markdown(f"<h3 style='margin:0;'>{status_icon}</h3>", unsafe_allow_html=True)
        
        st.markdown(f'<div style="height: 2px; background-color: {border_color}; margin: 10px 0;"></div>', 
                   unsafe_allow_html=True)


def render_logs(logs: list):
    """Render the logs viewer"""
    
    if not logs:
        st.info("No logs yet")
        return
    
    # Filter options
    col1, col2 = st.columns([3, 1])
    with col1:
        show_level = st.multiselect(
            "Filter by level:",
            ["INFO", "WARNING", "ERROR"],
            default=["INFO", "WARNING", "ERROR"]
        )
    
    # Display logs
    log_html = []
    for log in reversed(logs):  # Show most recent first
        if log["level"] in show_level:
            level_color = {
                "INFO": "#17a2b8",
                "WARNING": "#ffc107",
                "ERROR": "#dc3545"
            }.get(log["level"], "#6c757d")
            
            timestamp = log["time"].strftime("%H:%M:%S")
            
            log_html.append(
                f'<div style="margin: 5px 0; padding: 8px; background-color: #f8f9fa; border-left: 3px solid {level_color};">'
                f'<span style="color: #6c757d; font-size: 0.85rem;">{timestamp}</span> '
                f'<span style="color: {level_color}; font-weight: bold;">[{log["level"]}]</span> '
                f'<span>{log["message"]}</span>'
                f'</div>'
            )
    
    if log_html:
        st.markdown(
            '<div style="max-height: 400px; overflow-y: auto;">' +
            ''.join(log_html) +
            '</div>',
            unsafe_allow_html=True
        )
    else:
        st.info("No logs match the selected filters")


def create_progress_tracker():
    """Create and initialize a progress tracker in session state"""
    if 'progress_tracker' not in st.session_state:
        st.session_state.progress_tracker = PipelineProgressTracker()
    return st.session_state.progress_tracker
