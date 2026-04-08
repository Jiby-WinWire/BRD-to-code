"""
Visual BRD Editor Component with Drag-and-Drop
"""

import streamlit as st
from streamlit_sortables import sort_items
import json


def render_brd_editor():
    """Render the visual BRD editor with drag-and-drop capabilities"""
    
    st.markdown("### 🎨 Visual BRD Builder")
    st.markdown("Build your Business Requirements Document interactively")
    
    # Initialize BRD structure in session state
    if 'visual_brd' not in st.session_state:
        st.session_state.visual_brd = {
            'title': '',
            'description': '',
            'businessGoals': [],
            'functionalRequirements': [],
            'nonFunctionalRequirements': [],
            'stakeholders': [],
            'acceptanceCriteria': []
        }
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📋 Basic Info",
        "🎯 Business Goals",
        "⚙️ Functional Requirements",
        "🔧 Non-Functional Req.",
        "👥 Stakeholders",
        "✅ Acceptance Criteria"
    ])
    
    with tab1:
        render_basic_info()
    
    with tab2:
        render_business_goals()
    
    with tab3:
        render_functional_requirements()
    
    with tab4:
        render_nonfunctional_requirements()
    
    with tab5:
        render_stakeholders()
    
    with tab6:
        render_acceptance_criteria()
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Save BRD", type="primary", use_container_width=True):
            save_brd()
    
    with col2:
        if st.button("📥 Export JSON", use_container_width=True):
            export_brd_json()
    
    with col3:
        if st.button("▶️ Generate Code from BRD", type="primary", use_container_width=True):
            st.session_state.brd_data = st.session_state.visual_brd
            st.session_state.pipeline_started = True
            st.success("✅ BRD submitted to pipeline!")
            st.rerun()


def render_basic_info():
    """Render basic information section"""
    st.markdown("**Project Information**")
    
    title = st.text_input(
        "Project Title*",
        value=st.session_state.visual_brd.get('title', ''),
        placeholder="e.g., Blog Management API",
        key="brd_title"
    )
    
    description = st.text_area(
        "Description*",
        value=st.session_state.visual_brd.get('description', ''),
        placeholder="Brief description of the project and its purpose",
        height=150,
        key="brd_description"
    )
    
    # Update session state
    st.session_state.visual_brd['title'] = title
    st.session_state.visual_brd['description'] = description
    
    # Preview
    if title or description:
        with st.expander("📄 Preview"):
            st.markdown(f"**Title:** {title}")
            st.markdown(f"**Description:** {description}")


def render_business_goals():
    """Render business goals section with drag-and-drop"""
    st.markdown("**Business Goals**")
    st.caption("Add and reorder business goals for your project")
    
    # Initialize goals list
    if 'business_goals' not in st.session_state:
        st.session_state.business_goals = st.session_state.visual_brd.get('businessGoals', [])
    
    # Add new goal
    col1, col2 = st.columns([4, 1])
    with col1:
        new_goal = st.text_input("New Business Goal", key="new_business_goal")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", key="add_goal"):
            if new_goal:
                st.session_state.business_goals.append(new_goal)
                st.session_state.visual_brd['businessGoals'] = st.session_state.business_goals
                st.rerun()
    
    # Display existing goals with delete option
    if st.session_state.business_goals:
        st.markdown("**Current Goals** (drag to reorder):")
        
        for i, goal in enumerate(st.session_state.business_goals):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"{i+1}. {goal}")
            with col2:
                if st.button("🗑️", key=f"delete_goal_{i}"):
                    st.session_state.business_goals.pop(i)
                    st.session_state.visual_brd['businessGoals'] = st.session_state.business_goals
                    st.rerun()
    else:
        st.info("No business goals added yet. Add your first goal above!")


def render_functional_requirements():
    """Render functional requirements section"""
    st.markdown("**Functional Requirements**")
    st.caption("Define what the system should do")
    
    # Initialize FR list
    if 'functional_reqs' not in st.session_state:
        st.session_state.functional_reqs = st.session_state.visual_brd.get('functionalRequirements', [])
    
    # Add new FR
    col1, col2 = st.columns([4, 1])
    with col1:
        new_fr = st.text_input("New Functional Requirement", key="new_fr")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", key="add_fr"):
            if new_fr:
                fr_id = f"FR{len(st.session_state.functional_reqs) + 1}"
                st.session_state.functional_reqs.append({
                    'id': fr_id,
                    'description': new_fr
                })
                st.session_state.visual_brd['functionalRequirements'] = st.session_state.functional_reqs
                st.rerun()
    
    # Display existing FRs
    if st.session_state.functional_reqs:
        st.markdown("**Current Requirements:**")
        
        for i, req in enumerate(st.session_state.functional_reqs):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{req['id']}:** {req['description']}")
            with col2:
                if st.button("🗑️", key=f"delete_fr_{i}"):
                    st.session_state.functional_reqs.pop(i)
                    st.session_state.visual_brd['functionalRequirements'] = st.session_state.functional_reqs
                    st.rerun()
    else:
        st.info("No functional requirements added yet.")


def render_nonfunctional_requirements():
    """Render non-functional requirements section"""
    st.markdown("**Non-Functional Requirements**")
    st.caption("Define quality attributes and constraints")
    
    # Predefined NFR templates
    st.markdown("**Quick Add Templates:**")
    templates = {
        "Performance": "The API shall respond to all requests within 500ms under normal load conditions.",
        "RESTful": "The API shall be built using RESTful principles.",
        "Error Handling": "The API shall include proper error handling and return appropriate HTTP status codes.",
        "Data Format": "The API shall support JSON as the data format for requests and responses.",
        "Security": "The API shall be secure, ensuring that unauthorized users cannot access or modify data."
    }
    
    cols = st.columns(len(templates))
    for col, (name, desc) in zip(cols, templates.items()):
        with col:
            if st.button(f"➕ {name}", key=f"template_{name}", use_container_width=True):
                if 'nonfunctional_reqs' not in st.session_state:
                    st.session_state.nonfunctional_reqs = []
                
                nfr_id = f"NFR{len(st.session_state.nonfunctional_reqs) + 1}"
                st.session_state.nonfunctional_reqs.append({
                    'id': nfr_id,
                    'description': desc
                })
                st.session_state.visual_brd['nonFunctionalRequirements'] = st.session_state.nonfunctional_reqs
                st.rerun()
    
    st.markdown("---")
    
    # Initialize NFR list
    if 'nonfunctional_reqs' not in st.session_state:
        st.session_state.nonfunctional_reqs = st.session_state.visual_brd.get('nonFunctionalRequirements', [])
    
    # Add custom NFR
    col1, col2 = st.columns([4, 1])
    with col1:
        new_nfr = st.text_input("Custom Non-Functional Requirement", key="new_nfr")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", key="add_nfr"):
            if new_nfr:
                nfr_id = f"NFR{len(st.session_state.nonfunctional_reqs) + 1}"
                st.session_state.nonfunctional_reqs.append({
                    'id': nfr_id,
                    'description': new_nfr
                })
                st.session_state.visual_brd['nonFunctionalRequirements'] = st.session_state.nonfunctional_reqs
                st.rerun()
    
    # Display existing NFRs
    if st.session_state.nonfunctional_reqs:
        st.markdown("**Current Requirements:**")
        
        for i, req in enumerate(st.session_state.nonfunctional_reqs):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{req['id']}:** {req['description']}")
            with col2:
                if st.button("🗑️", key=f"delete_nfr_{i}"):
                    st.session_state.nonfunctional_reqs.pop(i)
                    st.session_state.visual_brd['nonFunctionalRequirements'] = st.session_state.nonfunctional_reqs
                    st.rerun()


def render_stakeholders():
    """Render stakeholders section"""
    st.markdown("**Stakeholders**")
    st.caption("Define project stakeholders and their responsibilities")
    
    # Initialize stakeholders list
    if 'stakeholders' not in st.session_state:
        st.session_state.stakeholders = st.session_state.visual_brd.get('stakeholders', [])
    
    # Predefined roles
    predefined_roles = {
        "Product Owner": "Define the requirements and ensure the API meets business needs.",
        "Developer": "Implement the API based on the defined requirements.",
        "QA Engineer": "Test the API to ensure it meets functional and non-functional requirements.",
        "End User": "Use the API to manage data and perform operations."
    }
    
    st.markdown("**Quick Add:**")
    cols = st.columns(4)
    for col, (role, resp) in zip(cols, predefined_roles.items()):
        with col:
            if st.button(f"➕ {role}", key=f"stakeholder_{role}", use_container_width=True):
                st.session_state.stakeholders.append({
                    'role': role,
                    'responsibility': resp
                })
                st.session_state.visual_brd['stakeholders'] = st.session_state.stakeholders
                st.rerun()
    
    st.markdown("---")
    
    # Add custom stakeholder
    col1, col2, col3 = st.columns([2, 3, 1])
    with col1:
        new_role = st.text_input("Role", key="new_stakeholder_role")
    with col2:
        new_resp = st.text_input("Responsibility", key="new_stakeholder_resp")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", key="add_stakeholder"):
            if new_role and new_resp:
                st.session_state.stakeholders.append({
                    'role': new_role,
                    'responsibility': new_resp
                })
                st.session_state.visual_brd['stakeholders'] = st.session_state.stakeholders
                st.rerun()
    
    # Display existing stakeholders
    if st.session_state.stakeholders:
        st.markdown("**Current Stakeholders:**")
        
        for i, stakeholder in enumerate(st.session_state.stakeholders):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{stakeholder['role']}:** {stakeholder['responsibility']}")
            with col2:
                if st.button("🗑️", key=f"delete_stakeholder_{i}"):
                    st.session_state.stakeholders.pop(i)
                    st.session_state.visual_brd['stakeholders'] = st.session_state.stakeholders
                    st.rerun()


def render_acceptance_criteria():
    """Render acceptance criteria section"""
    st.markdown("**Acceptance Criteria**")
    st.caption("Define success criteria for the project")
    
    # Initialize AC list
    if 'acceptance_criteria' not in st.session_state:
        st.session_state.acceptance_criteria = st.session_state.visual_brd.get('acceptanceCriteria', [])
    
    # Add new AC
    col1, col2 = st.columns([4, 1])
    with col1:
        new_ac = st.text_input("New Acceptance Criterion", key="new_ac")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Add", key="add_ac"):
            if new_ac:
                ac_id = f"AC{len(st.session_state.acceptance_criteria) + 1}"
                st.session_state.acceptance_criteria.append({
                    'id': ac_id,
                    'description': new_ac
                })
                st.session_state.visual_brd['acceptanceCriteria'] = st.session_state.acceptance_criteria
                st.rerun()
    
    # Display existing ACs
    if st.session_state.acceptance_criteria:
        st.markdown("**Current Criteria:**")
        
        for i, ac in enumerate(st.session_state.acceptance_criteria):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{ac['id']}:** {ac['description']}")
            with col2:
                if st.button("🗑️", key=f"delete_ac_{i}"):
                    st.session_state.acceptance_criteria.pop(i)
                    st.session_state.visual_brd['acceptanceCriteria'] = st.session_state.acceptance_criteria
                    st.rerun()
    else:
        st.info("No acceptance criteria added yet.")


def save_brd():
    """Save BRD to file"""
    from pathlib import Path
    import json
    
    output_dir = Path("saved_brds")
    output_dir.mkdir(exist_ok=True)
    
    filename = st.session_state.visual_brd.get('title', 'untitled').replace(' ', '_').lower()
    filepath = output_dir / f"{filename}_brd.json"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(st.session_state.visual_brd, f, indent=2)
    
    st.success(f"✅ BRD saved to {filepath}")


def export_brd_json():
    """Export BRD as downloadable JSON"""
    import json
    
    brd_json = json.dumps(st.session_state.visual_brd, indent=2)
    
    st.download_button(
        label="📥 Download BRD JSON",
        data=brd_json,
        file_name=f"{st.session_state.visual_brd.get('title', 'brd').replace(' ', '_').lower()}.json",
        mime="application/json"
    )
