from html.parser import HTMLParser

class TagBalancer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []
        # Tags that don't need closing
        self.void_elements = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag not in self.void_elements:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in self.void_elements:
            return
            
        if not self.stack:
            self.errors.append(f"Unexpected closing tag </{tag}> at {self.getpos()}")
            return

        last_tag, pos = self.stack[-1]
        if last_tag == tag:
            self.stack.pop()
        else:
            # Simple mismatch handling - assumes no skip
            self.errors.append(f"Expected </{last_tag}> but found </{tag}> at {self.getpos()}. Opened at {pos}")
            # Try to recover: pop until match or give up
            # For this simple check, we just verify balance
            
    def check_file(self, content):
        self.feed(content)
        if self.stack:
            for tag, pos in self.stack:
                self.errors.append(f"Unclosed tag <{tag}> at {pos}")
        
        return self.errors

def main():
    with open("d:\\ARASTIMA_IZINLERI\\templates\\degerlendirme.html", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Pre-process Jinja2?
    # Simple HTML parser will choke on Jinja blocks if they look like tags.
    # But usually Jinja use {% %} and {{ }}.
    # We strip them? 
    # This is rough check.
    
    validator = TagBalancer()
    errors = validator.check_file(content)
    
    if errors:
        print("HTML Errors found:")
        for e in errors[:10]: # Limit output
            print(e)
    else:
        print("HTML Structure looks balanced (ignoring Jinja).")

if __name__ == "__main__":
    main()
