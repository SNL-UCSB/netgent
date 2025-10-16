def parse_dom(dom_data):
    if not dom_data or 'map' not in dom_data:
        return "No DOM data available.", {}
    
    elements_map = dom_data['map']
    highlighted_elements = []
    
    for _, element_data in elements_map.items():
        highlight_index = element_data.get('highlightIndex', None)
        if highlight_index is not None and element_data.get('isVisible', False):
            text = _extract_text_content(element_data, elements_map)
            tag_name = element_data.get('tagName', 'unknown')
            metadata = element_data.get('metadata', {})
            accessible_name = metadata.get('accessibleName', '')
            
            highlighted_elements.append({
                'highlight_index': highlight_index,
                'tag_name': tag_name,
                'text': text,
                'accessible_name': accessible_name,
                'metadata': metadata,
                'x': element_data.get('x', 0),
                'y': element_data.get('y', 0),
                'width': element_data.get('width', 0),
                'height': element_data.get('height', 0),
            })    
    
    highlighted_elements.sort(key=lambda x: x['highlight_index'])
        
    # Build prompt string
    prompt = []
    # Build dictionary with highlight indices as keys
    elements_dict = {}
    
    for element in highlighted_elements:
        text = element['text']
        aria_label = element['accessible_name']
        tag_name = element['tag_name']
        highlight_index = element['highlight_index']
        metadata = element['metadata']
        
        if text or aria_label:
            label = f"{highlight_index} (<{tag_name}/>): " + (f"Text: {text}" if text else "") + (f", Aria Label: {aria_label}" if aria_label else "")
        else:
            label = f"{highlight_index} (<{tag_name}/>): <empty/>"
        prompt.append(label)
            
            # For the dictionary - updated format
        elements_dict[str(highlight_index)] = {
            'accessible_name': metadata.get('accessibleName', ''),
            'aria_role': metadata.get('ariaRole', ''),
            'css_selector': metadata.get('cssSelector', ''),
            'enhanced_css_selector': metadata.get('enhancedCssSelector', ''),
            'tag_name': metadata.get('tagName', tag_name),
            'text': metadata.get('text', text),
            'xpath': metadata.get('xpath', ''),
            'x': metadata.get('x', 0),
            'y': metadata.get('y', 0),
            'width': metadata.get('width', 0),
            'height': metadata.get('height', 0),
        }
    
    if not prompt:
        return "No highlighted elements found.", {}
    
    prompt_string = "\n".join(prompt)
    return prompt_string, elements_dict


def _extract_text_content(element_data, elements_map):
    """Extract meaningful text content from an element."""
    # Direct text content
    if 'text' in element_data:
        return element_data['text'].strip()
    
    # Check for text in children
    if 'children' in element_data:
        text_parts = []
        for child_id in element_data['children']:
            if child_id in elements_map:
                child = elements_map[child_id]
                if child.get('type') == 'TEXT_NODE' and 'text' in child:
                    text_parts.append(child['text'].strip())
        if text_parts:
            return " ".join(text_parts)
    
    # Fallback to common attributes
    attributes = element_data.get('attributes', {})
    for attr in ['aria-label', 'title', 'alt', 'placeholder', 'value']:
        if attr in attributes and attributes[attr]:
            return attributes[attr].strip()
    
    return ""

