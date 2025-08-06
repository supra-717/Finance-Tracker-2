import streamlit.components.v1 as components


def clear_inputs_on_focus(labels: list[str]) -> None:
    """Attach JS to clear inputs matching ``labels`` when focused."""

    script_parts = []
    for idx, label in enumerate(labels):
        script_parts.append(
            f"""
            const els{idx} = parent.document.querySelectorAll('input[aria-label="{label}"]');
            els{idx}.forEach((el) => {{
                el.addEventListener('focus', () => {{
                    if (el.value !== '') {{
                        el.value = '';
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }});
            }});
            """
        )
    components.html(f"<script>{''.join(script_parts)}</script>", height=0)
