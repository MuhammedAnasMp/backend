import re

def extract_instagram_id(url: str) -> str:
    """
    Extracts the unique shortcode/ID from an Instagram Reel or Post URL.
    Examples:
    - https://www.instagram.com/reel/DBabc123/ -> DBabc123
    - https://www.instagram.com/p/DBabc123/ -> DBabc123
    """
    # Pattern to match /reel/SHORTCODE or /p/SHORTCODE
    pattern = r'(?:https?://)?(?:www\.)?instagram\.com/(?:reel|p)/([^/?#&]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None
