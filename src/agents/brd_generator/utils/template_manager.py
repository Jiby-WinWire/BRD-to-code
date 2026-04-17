"""Simple Template Manager for BRD Generator

Manages BRD templates and provides automatic template selection.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SimpleBRDTemplateManager:
    """Manages BRD templates and provides template selection"""
    
    def __init__(self, templates_dir: str = None):
        """Initialize template manager
        
        Args:
            templates_dir: Path to templates directory (optional)
        """
        if templates_dir is None:
            current_dir = Path(__file__).parent.parent
            templates_dir = current_dir / "templates"
        
        self.templates_dir = Path(templates_dir)
        self._templates = {}
        self._config = {}
        self._load_config()
        self._load_templates()
    
    def _load_config(self):
        """Load template selection configuration"""
        config_file = self.templates_dir / "template_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                logger.info("Template configuration loaded")
            except Exception as e:
                logger.warning(f"Failed to load template config: {e}")
                self._config = {"template_selection_rules": {"default_template": "standard_brd"}}
        else:
            logger.warning("Template configuration not found, using defaults")
            self._config = {"template_selection_rules": {"default_template": "standard_brd"}}
    
    def _load_templates(self):
        """Load all template JSON files"""
        if not self.templates_dir.exists():
            logger.error(f"Templates directory not found: {self.templates_dir}")
            return
        
        for template_file in self.templates_dir.glob("*.json"):
            # Skip config files
            if template_file.name == "template_config.json":
                continue
            
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    template_id = template_data.get('template_id')
                    if template_id:
                        self._templates[template_id] = template_data
                        logger.info(f"Loaded BRD template: {template_id} ({template_data.get('template_name')})")
                    else:
                        logger.warning(f"Template file {template_file} missing template_id")
            except Exception as e:
                logger.error(f"Error loading template {template_file}: {e}")
    
    def get_template(self, template_id: str = "standard_brd") -> Optional[Dict[str, Any]]:
        """Get a specific template by ID
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template data dictionary or None
        """
        template = self._templates.get(template_id)
        if not template:
            logger.warning(f"Template '{template_id}' not found, falling back to standard_brd")
            template = self._templates.get("standard_brd")
        return template
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get list of available templates with metadata
        
        Returns:
            List of template metadata dictionaries
        """
        return [
            {
                'template_id': tid,
                'template_name': tdata.get('template_name', 'Unknown'),
                'description': tdata.get('description', ''),
                'use_case': tdata.get('use_case', '')
            }
            for tid, tdata in self._templates.items()
        ]
    
    def get_template_instructions(self, template_id: str) -> str:
        """Generate instructions to inject into LLM prompt
        
        Args:
            template_id: Template identifier
            
        Returns:
            Instruction text for LLM
        """
        template = self.get_template(template_id)
        if not template:
            return ""
        
        instructions = []
        instructions.append(f"\n{'='*80}")
        instructions.append(f"TEMPLATE: {template.get('template_name', 'Unknown')}")
        instructions.append(f"{'='*80}")
        instructions.append(f"Use Case: {template.get('use_case', 'General')}\n")
        
        # Required sections
        required_sections = [s for s in template.get('sections', []) if s.get('required', False)]
        if required_sections:
            instructions.append("REQUIRED SECTIONS TO INCLUDE:")
            for i, section in enumerate(required_sections, 1):
                instructions.append(f"\n{i}. {section.get('title', 'Unknown')}")
                if section.get('description'):
                    instructions.append(f"   Purpose: {section.get('description')}")
                if section.get('subsections'):
                    instructions.append("   Must include:")
                    for subsection in section['subsections']:
                        instructions.append(f"   • {subsection}")
        
        # Optional sections
        optional_sections = [s for s in template.get('sections', []) if not s.get('required', False)]
        if optional_sections:
            instructions.append("\n\nOPTIONAL SECTIONS (include if relevant):")
            for section in optional_sections:
                instructions.append(f"  - {section.get('title', 'Unknown')}: {section.get('description', '')}")
        
        # Formatting preferences
        formatting = template.get('formatting', {})
        if formatting:
            instructions.append("\n\nDOCUMENT FORMATTING PREFERENCES:")
            instructions.append(f"  • Writing Style: {formatting.get('style', 'professional')}")
            instructions.append(f"  • Tone: {formatting.get('tone', 'business-professional')}")
            instructions.append(f"  • Detail Level: {formatting.get('length', 'comprehensive')}")
            if formatting.get('include_diagrams'):
                instructions.append("  • Include visual diagrams where appropriate (architecture, workflows, etc.)")
            if formatting.get('include_tables'):
                instructions.append("  • Use tables for structured data (requirements matrix, risk register, etc.)")
        
        instructions.append("="*80 + "\n")
        
        return "\n".join(instructions)
    
    def auto_select_template(self, user_prompt: str) -> str:
        """Automatically select template based on keywords in prompt
        
        Args:
            user_prompt: User's natural language requirements
            
        Returns:
            Selected template_id
        """
        prompt_lower = user_prompt.lower()
        
        # Get selection rules from config
        rules = self._config.get('template_selection_rules', {}).get('rules', [])
        default_template = self._config.get('template_selection_rules', {}).get('default_template', 'standard_brd')
        
        # Find highest priority matching rule
        best_match = None
        highest_priority = -1
        matched_keywords = []
        
        for rule in rules:
            keywords = rule.get('keywords', [])
            template = rule.get('template', '')
            priority = rule.get('priority', 0)
            
            # Check if any keywords match
            matching_keywords = [kw for kw in keywords if kw.lower() in prompt_lower]
            
            if matching_keywords and priority > highest_priority:
                best_match = template
                highest_priority = priority
                matched_keywords = matching_keywords
        
        # Select template
        if best_match and best_match in self._templates:
            logger.info(f"Auto-selected template: {best_match} (priority: {highest_priority})")
            logger.info(f"  Matched keywords: {', '.join(matched_keywords)}")
            return best_match
        else:
            logger.info(f"Auto-selected template: {default_template} (default - no specific match)")
            return default_template
    
    def validate_template(self, template_data: Dict[str, Any]) -> List[str]:
        """Validate a template structure
        
        Args:
            template_data: Template dictionary to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        required_fields = ['template_name', 'template_id', 'description', 'sections']
        for field in required_fields:
            if field not in template_data:
                errors.append(f"Missing required field: {field}")
        
        if 'sections' in template_data:
            sections = template_data['sections']
            if not isinstance(sections, list):
                errors.append("Sections must be a list")
            else:
                for i, section in enumerate(sections):
                    if not isinstance(section, dict):
                        errors.append(f"Section {i} must be a dictionary")
                        continue
                    
                    section_required_fields = ['section_id', 'title', 'required']
                    for field in section_required_fields:
                        if field not in section:
                            errors.append(f"Section {i} missing required field: {field}")
        
        return errors
    
    def add_user_template(self, template_data: Dict[str, Any]) -> str:
        """Add a user-uploaded template to the collection
        
        Args:
            template_data: Template dictionary
            
        Returns:
            template_id of added template
        """
        # Validate template
        errors = self.validate_template(template_data)
        if errors:
            raise ValueError(f"Invalid template: {', '.join(errors)}")
        
        template_id = template_data.get('template_id')
        
        # Add to in-memory collection
        self._templates[template_id] = template_data
        
        # Save to file
        template_file = self.templates_dir / f"{template_id}.json"
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Added user template: {template_id}")
        return template_id


# Global instance
_template_manager = None


def get_template_manager() -> SimpleBRDTemplateManager:
    """Get or create global template manager instance
    
    Returns:
        Global SimpleBRDTemplateManager instance
    """
    global _template_manager
    if _template_manager is None:
        _template_manager = SimpleBRDTemplateManager()
    return _template_manager
