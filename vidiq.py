import streamlit as st
import re
import random
import datetime
import requests
import statistics
import pandas as pd
from googleapiclient.discovery import build
import json
from collections import Counter

# --- 1. CONFIG ---
st.set_page_config(page_title="YouTube VidIQ Clone", page_icon="🚀", layout="wide")

# --- 2. CUSTOM STYLING ---
st.markdown("""
<style>
    .main {background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 1rem;}
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .score-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.2rem;
    }
    .suggestion-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        transition: transform 0.2s;
    }
    .suggestion-box:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# --- 3. DATABASE CONFIG ---
URL_DATABASE_ONLINE = "https://gist.githubusercontent.com/rhanierex/f2d76f11df8d550376d81b58124d3668/raw/0b58a1eb02a7cffc2261a1c8d353551f3337001c/gistfile1.txt"
FALLBACK_POWER_WORDS = ["secret", "best", "exposed", "tutorial", "guide", "how to", "tips", "tricks", "hacks", "ultimate", "complete", "full", "master", "proven", "amazing", "incredible", "perfect", "easy", "simple", "advanced"]
VIRAL_EMOJIS = ["🔥", "😱", "🔴", "✅", "❌", "🎵", "⚠️", "⚡", "🚀", "💰", "💯", "🤯", "😭", "😡", "😴", "🌙", "✨", "💤", "🌧️", "🎹", "👀", "💪", "🎯", "⭐", "🏆"]
STOP_WORDS = {"the", "and", "or", "for", "to", "in", "on", "at", "by", "with", "a", "an", "is", "it", "of", "that", "this", "video", "i", "you", "me", "we", "my", "your"}

# --- 4. LOAD DATA ---
@st.cache_data(ttl=600) 
def load_power_words(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0: 
                return data, "🟢 Online"
    except:
        pass
    return FALLBACK_POWER_WORDS, "🟠 Offline"

POWER_WORDS_DB, db_status = load_power_words(URL_DATABASE_ONLINE)

# --- 5. HELPER FUNCTIONS ---
def calculate_engagement_rate(stats):
    """Calculate video engagement rate"""
    try:
        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        if views == 0:
            return 0
        engagement = ((likes + comments) / views) * 100
        return round(engagement, 2)
    except:
        return 0

def extract_core_theme(title, keyword):
    """
    FIXED: Extract the ACTUAL theme/context from the title
    This preserves the original meaning while removing only the keyword
    """
    if not title:
        return ""
    
    # Remove keyword but keep the rest intact
    if keyword:
        # Case-insensitive removal
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        core = pattern.sub("", title).strip()
    else:
        core = title
    
    # Clean up extra spaces and punctuation
    core = re.sub(r'\s+', ' ', core)
    core = re.sub(r'^[:\-\|,\.\s]+', '', core)
    core = re.sub(r'[:\-\|,\.\s]+$', '', core)
    
    # If nothing left, extract meaningful words from original title
    if not core or len(core) < 3:
        # Extract meaningful words (skip stop words and keyword)
        words = re.findall(r'\b\w+\b', title.lower())
        meaningful = [w for w in words if w not in STOP_WORDS and (not keyword or w != keyword.lower())]
        
        if meaningful:
            # Take first 3-5 meaningful words
            core = ' '.join(meaningful[:5])
        else:
            core = "Guide"
    
    return core.strip()

def smart_truncate(text, max_length):
    """Smart text truncation at word boundaries"""
    if not text or len(text) <= max_length:
        return text
    
    truncated = text[:max_length-3]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."

def extract_keywords_from_title(title, top_n=5):
    """Extract important keywords from title"""
    if not title:
        return []
    words = re.findall(r'\b[a-z]{3,}\b', title.lower())
    filtered = [w for w in words if w not in STOP_WORDS]
    counter = Counter(filtered)
    return [word for word, _ in counter.most_common(top_n)]

def generate_tags(title, keyword, competitor_tags=None):
    """Generate SEO-optimized tags"""
    if not title:
        return [keyword.lower()] if keyword else []
    
    tags = set()
    year = datetime.datetime.now().year
    
    # Add main keyword
    if keyword:
        tags.add(keyword.lower())
        tags.add(f"{keyword.lower()} {year}")
        
        # Add keyword variations
        kw_words = keyword.lower().split()
        if len(kw_words) > 1:
            tags.add(kw_words[0])
            tags.add(' '.join(kw_words[:2]))
    
    # Extract from title
    clean_title = re.sub(r'[^\w\s]', '', title.lower())
    words = clean_title.split()
    
    for word in words:
        if word not in STOP_WORDS and len(word) > 2:
            tags.add(word)
            if len(tags) >= 12:
                break
    
    # Add competitor tags
    if competitor_tags:
        for tag in competitor_tags[:5]:
            if len(tags) < 18:
                tags.add(tag.lower())
    
    # Add common variations
    if keyword:
        tags.add(f"{keyword.lower()} tutorial")
        tags.add(f"how to {keyword.lower()}")
    
    return list(tags)[:20]

def generate_description(title, keyword, tags, video_length="10:00"):
    """Generate SEO-optimized description"""
    year = datetime.datetime.now().year
    month = datetime.datetime.now().strftime("%B")
    
    try:
        duration_mins = int(video_length.split(':')[0])
    except:
        duration_mins = 10
    
    tag_text = ', '.join(tags[:5]) if tags else keyword
    hashtags = ' '.join([f"#{tag.replace(' ', '')}" for tag in tags[:5]]) if tags else f"#{keyword.replace(' ', '')}"
    
    return f"""🎬 {title}

📌 **About This Video:**
In this comprehensive {video_length} video, we dive deep into **{keyword}**. Whether you're a beginner or looking to advance your skills, this {year} guide will help you master {keyword}.

⏱️ **Timestamps:**
0:00 - Introduction
0:45 - What is {keyword}?
2:30 - Step-by-step {keyword} tutorial
{max(duration_mins-3, 5)}:00 - Pro tips and advanced techniques
{max(duration_mins-2, 7)}:00 - Common mistakes to avoid
{max(duration_mins-1, 9)}:00 - Conclusion & next steps

🔥 **What You'll Learn:**
✅ Complete {keyword} fundamentals
✅ Practical examples and demonstrations
✅ Expert insights and strategies
✅ Proven techniques that work in {year}

💡 **Related Topics:**
{tag_text}

🔔 **Don't Forget to:**
• SUBSCRIBE for more {keyword} content
• LIKE if this video helped you
• COMMENT your questions below
• SHARE with anyone who needs this

📱 **Connect With Us:**
[Add your social media links here]

{hashtags}

---
© {year} | {keyword.title()} Tutorial | All Rights Reserved
"""

def generate_smart_suggestions(original_title, keyword, api_key=None, competitor_data=None):
    """
    FIXED: Generate suggestions that PRESERVE the original title's theme
    """
    suggestions = []
    year = datetime.datetime.now().year
    
    # Extract the ACTUAL theme from the original title
    theme = extract_core_theme(original_title, keyword)
    
    # If theme is empty or generic, use extracted keywords
    if not theme or theme.lower() in ['guide', 'tutorial', 'video']:
        theme_words = extract_keywords_from_title(original_title, top_n=3)
        if theme_words:
            theme = ' '.join(theme_words[:3])
        else:
            theme = "Complete Guide"
    
    # Analyze competitor patterns
    power_word = random.choice(POWER_WORDS_DB).upper()
    number = random.choice(['5', '7', '10'])
    emoji = random.choice(VIRAL_EMOJIS)
    
    if competitor_data and len(competitor_data) > 0:
        top_title = competitor_data[0].get('title', '')
        
        # Extract numbers from top videos
        numbers = re.findall(r'\d+', top_title)
        if numbers:
            number = numbers[0]
        
        # Find power words in competitor titles
        for word in POWER_WORDS_DB:
            if word.lower() in top_title.lower():
                power_word = word.upper()
                break
    
    # Ensure theme fits within length limits
    # Calculate space for other elements
    
    # FORMULA 1: Keyword-First with Theme
    # Template: "{Keyword}: {Theme} - {Power} {Year} {Emoji}"
    extra_1 = len(keyword) + len(power_word) + len(str(year)) + len(emoji) + 10
    allowed_theme_1 = 100 - extra_1
    theme_1 = smart_truncate(theme.title(), allowed_theme_1)
    sug1 = f"{keyword.title()}: {theme_1} - {power_word} {year} {emoji}"
    suggestions.append(sug1)
    
    # FORMULA 2: Number Hook with Theme
    # Template: "{Number} {Keyword} {Theme} You Need ({Year}) {Emoji}"
    extra_2 = len(number) + len(keyword) + len(str(year)) + len(emoji) + 15
    allowed_theme_2 = 100 - extra_2
    theme_2 = smart_truncate(theme.title(), allowed_theme_2)
    sug2 = f"{number} {keyword.title()} {theme_2} You Need ({year}) {emoji}"
    suggestions.append(sug2)
    
    # FORMULA 3: How-To Format with Theme
    # Template: "How to {Keyword}: {Theme} {Emoji} [{Year} {Power}]"
    extra_3 = len(keyword) + len(power_word) + len(str(year)) + len(emoji) + 18
    allowed_theme_3 = 100 - extra_3
    theme_3 = smart_truncate(theme, allowed_theme_3)
    sug3 = f"How to {keyword.title()}: {theme_3} {emoji} [{year} {power_word}]"
    suggestions.append(sug3)
    
    # FORMULA 4: Theme-First Approach
    # Template: "{Theme} - {Keyword} {Power} Guide {Year} {Emoji}"
    extra_4 = len(keyword) + len(power_word) + len(str(year)) + len(emoji) + 12
    allowed_theme_4 = 100 - extra_4
    theme_4 = smart_truncate(theme.title(), allowed_theme_4)
    sug4 = f"{theme_4} - {keyword.title()} {power_word} Guide {year} {emoji}"
    suggestions.append(sug4)
    
    # FORMULA 5: Power Word First with Theme
    # Template: "{Power} {Keyword} {Theme} | {Year} Tutorial {Emoji}"
    extra_5 = len(keyword) + len(power_word) + len(str(year)) + len(emoji) + 15
    allowed_theme_5 = 100 - extra_5
    theme_5 = smart_truncate(theme, allowed_theme_5)
    sug5 = f"{power_word} {keyword.title()} {theme_5} | {year} Tutorial {emoji}"
    suggestions.append(sug5)
    
    return suggestions

def analyze_title(title, keyword=""):
    """Comprehensive title SEO analysis"""
    score = 0
    checks = []
    
    if not title:
        return 0, [("error", "Title is empty")]
    
    title_len = len(title)
    
    # 1. Length Analysis (25 points)
    if 40 <= title_len <= 70:
        score += 25
        checks.append(("success", f"✅ Perfect Length ({title_len} chars) - Ideal for SEO"))
    elif 30 <= title_len <= 90:
        score += 20
        checks.append(("warning", f"⚠️ Good Length ({title_len} chars) - Can be optimized"))
    elif title_len < 30:
        score += 10
        checks.append(("error", f"❌ Too Short ({title_len} chars) - Add more details"))
    else:
        score += 5
        checks.append(("error", f"❌ Too Long ({title_len} chars) - Will be truncated"))
    
    # 2. Keyword Analysis (20 points)
    if keyword:
        kw_lower = keyword.lower()
        title_lower = title.lower()
        
        if kw_lower in title_lower:
            # Check position
            position = title_lower.find(kw_lower)
            title_start = re.sub(r'^[^a-zA-Z0-9]+', '', title_lower).strip()
            
            if title_start.startswith(kw_lower):
                score += 20
                checks.append(("success", "✅ Keyword at Beginning - Perfect for SEO!"))
            elif position < 30:
                score += 15
                checks.append(("success", "✅ Keyword in First Half - Good placement"))
            else:
                score += 10
                checks.append(("warning", "⚠️ Keyword Present - Move closer to start"))
        else:
            checks.append(("error", "❌ Keyword Missing - Critical for ranking!"))
    else:
        score += 20
    
    # 3. Power Words (15 points)
    found_power = [pw for pw in POWER_WORDS_DB if pw.lower() in title.lower()]
    if found_power:
        score += 15
        checks.append(("success", f"✅ Power Words: {', '.join(found_power[:2])}"))
    else:
        checks.append(("warning", "⚠️ No Power Words - Add 'BEST', 'ULTIMATE', etc."))
    
    # 4. Numbers (15 points)
    numbers = re.findall(r'\d+', title)
    if numbers:
        score += 15
        checks.append(("success", f"✅ Numbers: {', '.join(numbers)} - Boosts CTR by 36%"))
    else:
        checks.append(("info", "💡 Add Numbers - Proven to increase clicks"))
    
    # 5. Emoji (10 points)
    emojis = [e for e in VIRAL_EMOJIS if e in title]
    if emojis:
        score += 10
        checks.append(("success", f"✅ Emoji: {' '.join(emojis)} - Eye-catching"))
    else:
        checks.append(("info", "💡 Add Emoji - Increases visibility"))
    
    # 6. Engagement Elements (15 points)
    engagement_score = 0
    
    # Check for brackets/parentheses
    if '[' in title or '(' in title:
        engagement_score += 5
        checks.append(("success", "✅ Brackets Used - Adds context"))
    
    # Check for question mark
    if '?' in title:
        engagement_score += 5
        checks.append(("success", "✅ Question Format - Creates curiosity"))
    
    # Check for year
    current_year = str(datetime.datetime.now().year)
    if current_year in title:
        engagement_score += 5
        checks.append(("success", f"✅ Current Year ({current_year}) - Shows freshness"))
    
    # Penalty for all caps
    if title.isupper():
        engagement_score -= 10
        checks.append(("error", "❌ ALL CAPS - Looks spammy"))
    
    score += min(engagement_score, 15)
    
    return min(score, 100), checks

def get_keyword_metrics(api_key, keyword):
    """Get comprehensive keyword metrics from YouTube"""
    if not api_key or len(api_key) < 30:
        return None, "❌ Invalid API Key"
    
    if not keyword:
        return None, "❌ Keyword required"
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Search for videos
        search_res = youtube.search().list(
            q=keyword,
            type='video',
            part='id,snippet',
            maxResults=20,
            order='relevance',
            regionCode='ID'
        ).execute()
        
        if not search_res.get('items'):
            return None, f"❌ No videos found for '{keyword}'"
        
        # Get video IDs
        video_ids = [item['id']['videoId'] for item in search_res['items'] if 'videoId' in item.get('id', {})]
        
        if not video_ids:
            return None, "❌ No valid videos found"
        
        # Get detailed statistics
        stats_res = youtube.videos().list(
            id=','.join(video_ids),
            part='statistics,snippet,contentDetails'
        ).execute()
        
        # Process data
        metrics = []
        all_tags = []
        upload_times = []
        
        for item in stats_res.get('items', []):
            snippet = item.get('snippet', {})
            stats = item.get('statistics', {})
            
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            comments = int(stats.get('commentCount', 0))
            engagement = calculate_engagement_rate(stats)
            
            tags = snippet.get('tags', [])
            all_tags.extend(tags)
            
            published = snippet.get('publishedAt', '')
            if published:
                upload_times.append(published)
            
            metrics.append({
                'title': snippet.get('title', ''),
                'Title': snippet.get('title', 'Unknown'),
                'Views': views,
                'Likes': likes,
                'Comments': comments,
                'Engagement': engagement,
                'Channel': snippet.get('channelTitle', 'Unknown'),
                'Date': published[:10] if published else 'N/A',
                'tags': tags,
                'publishedAt': published
            })
        
        if not metrics:
            return None, "❌ No data available"
        
        # Create DataFrame
        df = pd.DataFrame(metrics)
        
        # Calculate metrics
        view_counts = [m['Views'] for m in metrics if m['Views'] > 0]
        engagement_rates = [m['Engagement'] for m in metrics if m['Engagement'] > 0]
        
        median_views = statistics.median(view_counts) if view_counts else 0
        avg_views = statistics.mean(view_counts) if view_counts else 0
        avg_engagement = statistics.mean(engagement_rates) if engagement_rates else 0
        
        # Trending tags
        trending_tags = []
        if all_tags:
            tag_counts = Counter(all_tags)
            trending_tags = [tag for tag, _ in tag_counts.most_common(15)]
        
        # Best upload time
        best_time = "Unknown"
        if upload_times:
            hours = [int(t[11:13]) for t in upload_times if len(t) > 13]
            if hours:
                most_common_hour = Counter(hours).most_common(1)[0][0]
                best_time = f"{most_common_hour:02d}:00 - {(most_common_hour+1):02d}:00 WIB"
        
        # Competition level
        if median_views > 500000:
            difficulty = "🔴 High"
            diff_score = 30
        elif median_views > 100000:
            difficulty = "🟡 Medium"
            diff_score = 60
        else:
            difficulty = "🟢 Low"
            diff_score = 90
        
        # Opportunity score
        opportunity_score = diff_score
        
        return {
            'median_views': median_views,
            'avg_views': avg_views,
            'avg_engagement': avg_engagement,
            'score': opportunity_score,
            'difficulty': difficulty,
            'difficulty_score': diff_score,
            'trending_tags': trending_tags,
            'best_upload_time': best_time,
            'total_videos': len(metrics),
            'top_videos': df,
            'competitor_data': metrics
        }, None
        
    except Exception as e:
        error_msg = str(e)
        if "API key not valid" in error_msg:
            return None, "❌ API Key tidak valid!"
        elif "quota" in error_msg.lower():
            return None, "❌ Quota API habis!"
        else:
            return None, f"❌ Error: {error_msg}"

# --- 6. UI COMPONENTS ---
def draw_competitor_chart(df):
    """Visualize competitor data"""
    if df is None or df.empty:
        st.warning("No data available")
        return
    
    st.markdown("### 📊 Top Competitor Videos")
    
    max_views = df['Views'].max()
    if max_views == 0:
        max_views = 1
    
    for idx, row in df.head(10).iterrows():
        title = row['Title']
        if len(title) > 60:
            title = title[:60] + "..."
        
        views = row['Views']
        engagement = row.get('Engagement', 0)
        width_pct = int((views / max_views) * 100)
        
        # Color based on engagement
        if engagement > 5:
            color = "#10b981"
        elif engagement > 2:
            color = "#f59e0b"
        else:
            color = "#ef4444"
        
        st.markdown(f"""
        <div style="background: #1e1e1e; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <div style="color: white; font-weight: bold; font-size: 14px; margin-bottom: 0.5rem;">{title}</div>
            <div style="color: #888; font-size: 12px; margin-bottom: 0.5rem;">
                {row['Channel']} • {views:,} views • {engagement}% engagement
            </div>
            <div style="background: #333; width: 100%; height: 10px; border-radius: 5px; overflow: hidden;">
                <div style="background: {color}; width: {width_pct}%; height: 10px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- 7. SIDEBAR ---
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    if "Online" in db_status:
        st.success(db_status)
    else:
        st.warning(db_status)
    
    st.divider()
    
    st.markdown("### 🔑 YouTube API")
    api_key = st.text_input("API Key:", type="password", placeholder="AIzaSy...")
    
    if api_key and len(api_key) > 30:
        st.success("🟢 Connected")
    elif api_key:
        st.warning("⚠️ Key too short")
    
    with st.expander("📖 Get API Key"):
        st.markdown("""
        1. Visit [Google Cloud Console](https://console.cloud.google.com)
        2. Create new project
        3. Enable YouTube Data API v3
        4. Create credentials (API Key)
        5. Copy & paste above
        """)
    
    st.divider()
    st.markdown("### 📊 Stats")
    st.metric("Power Words", len(POWER_WORDS_DB))
    st.metric("Viral Emojis", len(VIRAL_EMOJIS))

# --- 8. MAIN APP ---
st.markdown("""
<div style='text-align: center; color: white; margin-bottom: 2rem;'>
    <h1 style='font-size: 3.5rem; font-weight: 800; text-shadow: 2px 2px 10px rgba(0,0,0,0.3);'>🚀 YouTube VidIQ Clone</h1>
    <p style='color: #ddd; font-size: 1.2rem;'>Advanced YouTube SEO & Analytics Tool</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🔍 Keyword Research", "📝 Title Optimizer", "📺 Channel Audit", "🎯 Trend Finder"])

# TAB 1: KEYWORD RESEARCH
with tab1:
    st.markdown("### 🔍 Keyword Research & Analysis")
    
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        kw_input = st.text_input("Enter Keyword/Topic:", placeholder="e.g., lullaby sleeping music")
    with col_btn:
        st.write("")
        st.write("")
        analyze_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)
    
    if analyze_btn:
        if not api_key or len(api_key) < 30:
            st.error("⚠️ Please enter valid API Key in sidebar")
        elif not kw_input:
            st.warning("⚠️ Enter a keyword first")
        else:
            with st.spinner(f"🔄 Analyzing '{kw_input}'..."):
                data, err = get_keyword_metrics(api_key, kw_input)
                
                if err:
                    st.error(err)
                elif data:
                    st.success(f"✅ Analysis complete for '{kw_input}'")
                    
                    # Metrics
                    st.markdown("### 📊 Market Overview")
                    m1, m2, m3, m4 = st.columns(4)
                    
                    with m1:
                        st.metric("Opportunity", f"{data['score']}/100")
                    with m2:
                        st.metric("Competition", data['difficulty'])
                    with m3:
                        st.metric("Avg Views", f"{int(data['avg_views']):,}")
                    with m4:
                        st.metric("Videos Analyzed", data['total_videos'])
                    
                    st.divider()
                    
                    # Visuals
                    col_chart, col_tags = st.columns([2, 1])
                    
                    with col_chart:
                        draw_competitor_chart(data['top_videos'])
                    
                    with col_tags:
                        st.markdown("### 🏷️ Trending Tags")
                        if data['trending_tags']:
                            for tag in data['trending_tags'][:10]:
                                st.code(tag, language='text')
                        
                        st.divider()
                        st.markdown("### ⏰ Best Upload Time")
                        st.info(data['best_upload_time'])

# TAB 2: TITLE OPTIMIZER (FIXED)
with tab2:
    st.markdown("### ✍️ Title Optimizer")
    
    col_kw, col_title = st.columns([1, 2])
    with col_kw:
        keyword = st.text_input("🎯 Target Keyword:", placeholder="e.g., lullaby sleeping")
    with col_title:
        title = st.text_input("📝 Your Title:", placeholder="Paste your title here...")
    
    if st.button("🔍 Analyze & Get Suggestions", type="primary"):
        if not title:
            st.warning("⚠️ Enter a title to analyze")
        else:
            # Analyze current title
            score, checks = analyze_title(title, keyword)
            
            # Display score
            st.markdown("---")
            if score >= 80:
                color = "#10b981"
                grade = "A"
                msg = "Excellent!"
            elif score >= 60:
                color = "#f59e0b"
                grade = "B"
                msg = "Good"
            else:
                color = "#ef4444"
                grade = "C"
                msg = "Needs Work"
            
            col_score, col_grade = st.columns([4, 1])
            with col_score:
                st.markdown(f"""
                <div style='background: {color}22; padding: 1.5rem; border-radius: 10px; border-left: 5px solid {color};'>
                    <h2 style='color: {color}; margin: 0;'>SEO Score: {score}/100</h2>
                    <p style='color: #666; margin: 0.5rem 0 0 0;'>{msg} - Grade {grade}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_grade:
                st.markdown(f"<h1 style='color:{color}; text-align:center; font-size:4rem; margin:0;'>{grade}</h1>", unsafe_allow_html=True)
            
            # Analysis details
            st.markdown("---")
            st.markdown("### 📋 SEO Analysis")
            
            cols = st.columns(3)
            for i, (status, message) in enumerate(checks):
                with cols[i % 3]:
                    if status == "success":
                        st.success(message, icon="✅")
                    elif status == "warning":
                        st.warning(message, icon="⚠️")
                    elif status == "info":
                        st.info(message, icon="💡")
                    else:
                        st.error(message, icon="❌")
            
            # Generate suggestions if needed
            if score < 85 and keyword:
                st.markdown("---")
                st.markdown("### 💡 AI-Powered Title Suggestions")
                st.caption(f"**Original Theme Preserved:** These suggestions maintain your title's original context")
                
                # Show what theme was extracted
                extracted_theme = extract_core_theme(title, keyword)
                st.info(f"🎯 **Detected Theme:** {extracted_theme}")
                
                # Get competitor data if API available
                competitor_data = None
                if api_key and len(api_key) > 30:
                    with st.spinner("📊 Analyzing competitors..."):
                        result, _ = get_keyword_metrics(api_key, keyword)
                        if result:
                            competitor_data = result.get('competitor_data', [])
                
                # Generate suggestions
                suggestions = generate_smart_suggestions(title, keyword, api_key, competitor_data)
                
                for i, sug in enumerate(suggestions, 1):
                    sug_score, _ = analyze_title(sug, keyword)
                    
                    # Color based on improvement
                    if sug_score > score:
                        badge_color = "#10b981"
                        badge_text = f"🔥 +{sug_score - score} Better"
                    elif sug_score == score:
                        badge_color = "#3b82f6"
                        badge_text = "📊 Same Score"
                    else:
                        badge_color = "#f59e0b"
                        badge_text = "📝 Alternative"
                    
                    st.markdown(f"""
                    <div class="suggestion-box" style="border-left: 4px solid {badge_color};">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="font-weight: bold; font-size: 0.9rem;">{badge_text}</span>
                            <span style="font-weight: bold;">Score: {sug_score}/100</span>
                        </div>
                        <div style="font-size: 1rem; line-height: 1.4;">{sug}</div>
                        <div style="margin-top: 0.5rem; font-size: 0.85rem; opacity: 0.8;">
                            Length: {len(sug)} chars
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Copy button
                    if st.button(f"📋 Copy Suggestion #{i}", key=f"copy_sug_{i}"):
                        st.code(sug, language='text')
            
            # Tags & Description
            st.markdown("---")
            st.markdown("### 🎁 Complete Metadata Package")
            
            tab_tags, tab_desc = st.tabs(["🏷️ Tags", "📄 Description"])
            
            # Get trending tags if available
            trending_tags = []
            if api_key and len(api_key) > 30 and keyword:
                with st.spinner("Getting trending tags..."):
                    result, _ = get_keyword_metrics(api_key, keyword)
                    if result:
                        trending_tags = result.get('trending_tags', [])
            
            generated_tags = generate_tags(title, keyword, trending_tags)
            
            with tab_tags:
                st.text_area(
                    "📋 Copy These Tags:",
                    ", ".join(generated_tags),
                    height=200,
                    help="Optimized tags based on your title and trending topics"
                )
                st.caption(f"✅ {len(generated_tags)} tags generated | {len(', '.join(generated_tags))} characters")
            
            with tab_desc:
                description = generate_description(title, keyword, generated_tags)
                st.text_area(
                    "📋 Copy This Description:",
                    description,
                    height=300,
                    help="SEO-optimized description with timestamps and CTAs"
                )
                st.caption(f"✅ {len(description)} characters | Includes timestamps, hashtags & CTAs")

# TAB 3: CHANNEL AUDIT
with tab3:
    st.markdown("### 📺 Channel Performance Audit")
    
    col_id, col_limit, col_btn = st.columns([3, 1, 1])
    with col_id:
        channel_id = st.text_input("Channel ID (UC...):", placeholder="UC_x5XG1OV2P6uZZ5FSM9Ttw")
    with col_limit:
        video_limit = st.selectbox("Videos", [5, 10, 15, 20], index=1)
    with col_btn:
        st.write("")
        st.write("")
        audit_btn = st.button("🔍 Audit", type="primary", use_container_width=True)
    
    if audit_btn:
        if not api_key or len(api_key) < 30:
            st.error("⚠️ API Key required")
        elif not channel_id or not channel_id.startswith("UC"):
            st.error("⚠️ Invalid Channel ID (must start with UC)")
        else:
            with st.spinner("🔄 Auditing channel..."):
                try:
                    yt = build('youtube', 'v3', developerKey=api_key)
                    
                    # Get channel info
                    ch_res = yt.channels().list(
                        id=channel_id,
                        part='snippet,statistics,contentDetails'
                    ).execute()
                    
                    if not ch_res.get('items'):
                        st.error("❌ Channel not found")
                    else:
                        ch = ch_res['items'][0]
                        snippet = ch['snippet']
                        stats = ch['statistics']
                        
                        # Channel header
                        st.markdown("---")
                        col_img, col_info = st.columns([1, 4])
                        
                        with col_img:
                            st.image(snippet['thumbnails']['medium']['url'], width=150)
                        
                        with col_info:
                            st.markdown(f"## {snippet['title']}")
                            st.caption(snippet.get('description', '')[:200] + "...")
                            
                            m1, m2, m3, m4 = st.columns(4)
                            with m1:
                                st.metric("👥 Subscribers", f"{int(stats.get('subscriberCount', 0)):,}")
                            with m2:
                                st.metric("👁️ Total Views", f"{int(stats['viewCount']):,}")
                            with m3:
                                st.metric("🎬 Videos", f"{int(stats['videoCount']):,}")
                            with m4:
                                avg = int(stats['viewCount']) / max(int(stats['videoCount']), 1)
                                st.metric("📊 Avg Views", f"{int(avg):,}")
                        
                        st.markdown("---")
                        
                        # Get videos
                        upload_id = ch['contentDetails']['relatedPlaylists']['uploads']
                        vids_res = yt.playlistItems().list(
                            playlistId=upload_id,
                            part='snippet',
                            maxResults=video_limit
                        ).execute()
                        
                        st.markdown(f"### 📹 Analyzing {len(vids_res['items'])} Recent Videos")
                        
                        total_score = 0
                        video_scores = []
                        
                        for idx, item in enumerate(vids_res['items'], 1):
                            vid_title = item['snippet']['title']
                            vid_thumb = item['snippet']['thumbnails']['default']['url']
                            vid_date = item['snippet']['publishedAt'][:10]
                            
                            # Extract keyword
                            vid_keywords = extract_keywords_from_title(vid_title, top_n=1)
                            vid_keyword = vid_keywords[0] if vid_keywords else ""
                            
                            # Analyze
                            vid_score, vid_checks = analyze_title(vid_title, vid_keyword)
                            total_score += vid_score
                            video_scores.append(vid_score)
                            
                            # Display
                            with st.container():
                                col_thumb, col_content, col_score = st.columns([1, 5, 1])
                                
                                with col_thumb:
                                    st.image(vid_thumb, width=120)
                                
                                with col_content:
                                    st.markdown(f"**#{idx}. {vid_title}**")
                                    st.caption(f"📅 {vid_date}")
                                    
                                    if vid_score >= 80:
                                        st.success(f"✅ Excellent SEO ({vid_score}/100)", icon="🔥")
                                    elif vid_score >= 60:
                                        st.warning(f"⚠️ Good SEO ({vid_score}/100)", icon="📈")
                                    else:
                                        st.error(f"❌ Needs optimization ({vid_score}/100)", icon="⚠️")
                                    
                                    if vid_score < 80:
                                        with st.expander("💡 See Improvement Suggestions"):
                                            suggestions = generate_smart_suggestions(vid_title, vid_keyword, api_key)
                                            for sug in suggestions[:3]:
                                                st.code(sug, language='text')
                                
                                with col_score:
                                    score_color = "#10b981" if vid_score >= 80 else "#f59e0b" if vid_score >= 60 else "#ef4444"
                                    st.markdown(f"""
                                    <div style="text-align: center;">
                                        <div style="font-size: 2.5rem; font-weight: bold; color: {score_color};">{vid_score}</div>
                                        <div style="font-size: 0.8rem; color: #666;">Score</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                st.divider()
                        
                        # Channel summary
                        if video_scores:
                            st.markdown("---")
                            st.markdown("### 📊 Channel SEO Summary")
                            
                            avg_score = total_score / len(video_scores)
                            excellent = sum(1 for s in video_scores if s >= 80)
                            good = sum(1 for s in video_scores if 60 <= s < 80)
                            poor = sum(1 for s in video_scores if s < 60)
                            
                            m1, m2, m3, m4 = st.columns(4)
                            with m1:
                                st.metric("Average Score", f"{int(avg_score)}/100")
                            with m2:
                                st.metric("🔥 Excellent", f"{excellent}/{len(video_scores)}")
                            with m3:
                                st.metric("📈 Good", f"{good}/{len(video_scores)}")
                            with m4:
                                st.metric("⚠️ Needs Work", f"{poor}/{len(video_scores)}")
                            
                            # Recommendations
                            st.markdown("---")
                            st.markdown("### 💡 Overall Recommendations")
                            
                            if avg_score >= 80:
                                st.success("✅ **Excellent Channel SEO!** Your titles are highly optimized. Keep up the great work!")
                            elif avg_score >= 60:
                                st.warning(f"⚠️ **Good Channel SEO** - You're on the right track! Focus on optimizing the {poor} videos that need work.")
                            else:
                                st.error(f"🔴 **SEO Needs Improvement** - {poor} videos need optimization. Use the Title Optimizer tab to improve each title.")
                            
                            # Action items
                            if poor > 0:
                                st.info(f"""
                                **Action Items:**
                                - Optimize {poor} low-scoring videos using AI suggestions
                                - Add keywords at the beginning of titles
                                - Include power words and numbers
                                - Use emojis for better visibility
                                """)
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.caption("Check your API key and Channel ID")

# TAB 4: TREND FINDER (Enhanced UI)
with tab4:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; margin-bottom: 2rem;'>
        <h2 style='color: white; margin: 0; text-align: center;'>🎯 Discover Trending Topics</h2>
        <p style='color: #f0f0f0; text-align: center; margin: 0.5rem 0 0 0;'>Find what's hot in your niche right now</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_niche, col_days, col_btn = st.columns([3, 1, 1])
    with col_niche:
        niche = st.text_input("🎨 Your Niche/Category:", placeholder="e.g., gaming, cooking, music, tech reviews")
    with col_days:
        days_filter = st.selectbox("Period", ["7 Days", "14 Days", "30 Days"], index=0)
    with col_btn:
        st.write("")
        st.write("")
        trend_btn = st.button("🔥 Find Trends", type="primary", use_container_width=True)
    
    if trend_btn:
        if not api_key or len(api_key) < 30:
            st.error("⚠️ API Key required in sidebar")
        elif not niche:
            st.warning("⚠️ Enter your niche first")
        else:
            # Parse days
            days = int(days_filter.split()[0])
            
            with st.spinner(f"🔍 Analyzing trending videos in '{niche}' (last {days} days)..."):
                try:
                    yt = build('youtube', 'v3', developerKey=api_key)
                    
                    # Calculate date filter
                    published_after = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat() + 'Z'
                    
                    # Search trending videos
                    trends_res = yt.search().list(
                        q=niche,
                        type='video',
                        part='id,snippet',
                        maxResults=20,
                        order='viewCount',
                        publishedAfter=published_after,
                        regionCode='ID'
                    ).execute()
                    
                    if not trends_res.get('items'):
                        st.warning(f"No trending videos found for '{niche}' in the last {days} days")
                    else:
                        video_ids = [item['id']['videoId'] for item in trends_res['items'] if 'videoId' in item.get('id', {})]
                        
                        # Get detailed stats
                        stats_res = yt.videos().list(
                            id=','.join(video_ids),
                            part='statistics,snippet,contentDetails'
                        ).execute()
                        
                        if stats_res.get('items'):
                            st.success(f"✅ Found {len(stats_res['items'])} trending videos in the last {days} days!")
                            
                            # Extract data
                            all_words = []
                            all_tags = []
                            all_emojis = []
                            trend_data = []
                            
                            for item in stats_res['items']:
                                snippet = item['snippet']
                                stats = item['statistics']
                                
                                title = snippet['title']
                                tags = snippet.get('tags', [])
                                views = int(stats.get('viewCount', 0))
                                engagement = calculate_engagement_rate(stats)
                                
                                # Extract words
                                words = re.findall(r'\b[a-zA-Z]{4,}\b', title.lower())
                                all_words.extend([w for w in words if w not in STOP_WORDS])
                                
                                # Extract tags
                                all_tags.extend(tags)
                                
                                # Extract emojis
                                emojis = [char for char in title if char in VIRAL_EMOJIS]
                                all_emojis.extend(emojis)
                                
                                trend_data.append({
                                    'title': title,
                                    'channel': snippet['channelTitle'],
                                    'views': views,
                                    'engagement': engagement,
                                    'thumbnail': snippet['thumbnails']['medium']['url'],
                                    'published': snippet['publishedAt'][:10]
                                })
                            
                            # Calculate trending patterns
                            word_counts = Counter(all_words)
                            tag_counts = Counter(all_tags)
                            emoji_counts = Counter(all_emojis)
                            
                            # Sort trend data by views
                            trend_data.sort(key=lambda x: x['views'], reverse=True)
                            
                            # === INSIGHTS SECTION ===
                            st.markdown("---")
                            st.markdown("### 📊 Trend Intelligence Dashboard")
                            
                            # Top metrics
                            total_views = sum(d['views'] for d in trend_data)
                            avg_engagement = sum(d['engagement'] for d in trend_data) / len(trend_data) if trend_data else 0
                            
                            m1, m2, m3, m4 = st.columns(4)
                            with m1:
                                st.metric("🔥 Trending Videos", len(trend_data))
                            with m2:
                                st.metric("👁️ Total Views", f"{total_views:,}")
                            with m3:
                                st.metric("📈 Avg Engagement", f"{avg_engagement:.2f}%")
                            with m4:
                                st.metric("🏷️ Unique Tags", len(set(all_tags)))
                            
                            st.markdown("---")
                            
                            # === THREE COLUMN INSIGHTS ===
                            col_keywords, col_tags, col_emojis = st.columns(3)
                            
                            with col_keywords:
                                st.markdown("""
                                <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 12px; height: 400px; overflow-y: auto;'>
                                    <h3 style='color: white; margin-top: 0;'>🔥 Hot Keywords</h3>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                for word, count in word_counts.most_common(12):
                                    # Calculate popularity bar
                                    max_count = word_counts.most_common(1)[0][1]
                                    width = int((count / max_count) * 100)
                                    
                                    st.markdown(f"""
                                    <div style='background: rgba(255,255,255,0.2); padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem;'>
                                        <div style='display: flex; justify-content: space-between; margin-bottom: 0.3rem;'>
                                            <span style='color: white; font-weight: bold; font-size: 0.95rem;'>{word.title()}</span>
                                            <span style='color: #fff; background: rgba(255,255,255,0.3); padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem;'>{count}x</span>
                                        </div>
                                        <div style='background: rgba(255,255,255,0.3); height: 6px; border-radius: 3px; overflow: hidden;'>
                                            <div style='background: white; width: {width}%; height: 6px;'></div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            with col_tags:
                                st.markdown("""
                                <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1.5rem; border-radius: 12px; height: 400px; overflow-y: auto;'>
                                    <h3 style='color: white; margin-top: 0;'>🏷️ Trending Tags</h3>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                for tag, count in tag_counts.most_common(12):
                                    max_tag_count = tag_counts.most_common(1)[0][1]
                                    tag_width = int((count / max_tag_count) * 100)
                                    
                                    st.markdown(f"""
                                    <div style='background: rgba(255,255,255,0.2); padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem;'>
                                        <div style='display: flex; justify-content: space-between; margin-bottom: 0.3rem;'>
                                            <span style='color: white; font-weight: bold; font-size: 0.95rem;'>#{tag}</span>
                                            <span style='color: #fff; background: rgba(255,255,255,0.3); padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem;'>{count} videos</span>
                                        </div>
                                        <div style='background: rgba(255,255,255,0.3); height: 6px; border-radius: 3px; overflow: hidden;'>
                                            <div style='background: white; width: {tag_width}%; height: 6px;'></div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            
                            with col_emojis:
                                st.markdown("""
                                <div style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 1.5rem; border-radius: 12px; height: 400px; overflow-y: auto;'>
                                    <h3 style='color: white; margin-top: 0;'>✨ Popular Emojis</h3>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                if emoji_counts:
                                    for emoji, count in emoji_counts.most_common(10):
                                        max_emoji_count = emoji_counts.most_common(1)[0][1]
                                        emoji_width = int((count / max_emoji_count) * 100)
                                        
                                        st.markdown(f"""
                                        <div style='background: rgba(255,255,255,0.2); padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem;'>
                                            <div style='display: flex; justify-content: space-between; margin-bottom: 0.3rem;'>
                                                <span style='font-size: 1.5rem;'>{emoji}</span>
                                                <span style='color: #fff; background: rgba(255,255,255,0.3); padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.8rem;'>{count}x</span>
                                            </div>
                                            <div style='background: rgba(255,255,255,0.3); height: 6px; border-radius: 3px; overflow: hidden;'>
                                                <div style='background: white; width: {emoji_width}%; height: 6px;'></div>
                                            </div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.markdown("<p style='color: white; text-align: center;'>No emojis detected</p>", unsafe_allow_html=True)
                            
                            # === TOP TRENDING VIDEOS ===
                            st.markdown("---")
                            st.markdown("### 🏆 Top Trending Videos")
                            
                            for idx, video in enumerate(trend_data[:8], 1):
                                # Determine rank color
                                if idx <= 3:
                                    rank_color = "#FFD700"  # Gold
                                    rank_icon = "🏆"
                                elif idx <= 5:
                                    rank_color = "#C0C0C0"  # Silver
                                    rank_icon = "🥈"
                                else:
                                    rank_color = "#CD7F32"  # Bronze
                                    rank_icon = "🥉"
                                
                                # Engagement color
                                if video['engagement'] > 5:
                                    eng_color = "#10b981"
                                    eng_label = "🔥 High"
                                elif video['engagement'] > 2:
                                    eng_color = "#f59e0b"
                                    eng_label = "📈 Good"
                                else:
                                    eng_color = "#6b7280"
                                    eng_label = "📊 Normal"
                                
                                st.markdown(f"""
                                <div style='background: linear-gradient(135deg, #667eea22 0%, #764ba222 100%); 
                                            padding: 1.5rem; border-radius: 12px; margin-bottom: 1rem; 
                                            border-left: 5px solid {rank_color};
                                            transition: transform 0.2s;'>
                                    <div style='display: flex; align-items: center; gap: 1rem;'>
                                        <div style='font-size: 2rem; font-weight: bold; color: {rank_color};'>
                                            {rank_icon} #{idx}
                                        </div>
                                        <div style='flex: 1;'>
                                            <h4 style='color: white; margin: 0 0 0.5rem 0; font-size: 1.1rem;'>{video['title']}</h4>
                                            <div style='display: flex; gap: 1.5rem; flex-wrap: wrap;'>
                                                <span style='color: #ddd; font-size: 0.9rem;'>
                                                    📺 {video['channel']}
                                                </span>
                                                <span style='color: #ddd; font-size: 0.9rem;'>
                                                    👁️ {video['views']:,} views
                                                </span>
                                                <span style='color: {eng_color}; font-size: 0.9rem; font-weight: bold;'>
                                                    {eng_label} ({video['engagement']:.2f}%)
                                                </span>
                                                <span style='color: #aaa; font-size: 0.9rem;'>
                                                    📅 {video['published']}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # === ACTIONABLE INSIGHTS ===
                            st.markdown("---")
                            st.markdown("### 💡 Actionable Insights")
                            
                            col_insights1, col_insights2 = st.columns(2)
                            
                            with col_insights1:
                                st.markdown("""
                                <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                            padding: 1.5rem; border-radius: 12px;'>
                                    <h4 style='color: white; margin-top: 0;'>📝 Title Strategy</h4>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                top_keywords = [word for word, _ in word_counts.most_common(5)]
                                st.success(f"✅ **Use these keywords:** {', '.join(top_keywords)}")
                                
                                if emoji_counts:
                                    top_emojis = [emoji for emoji, _ in emoji_counts.most_common(3)]
                                    st.info(f"✨ **Trending emojis:** {' '.join(top_emojis)}")
                                
                                avg_title_len = sum(len(v['title']) for v in trend_data) / len(trend_data)
                                st.warning(f"📏 **Optimal length:** ~{int(avg_title_len)} characters")
                            
                            with col_insights2:
                                st.markdown("""
                                <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                                            padding: 1.5rem; border-radius: 12px;'>
                                    <h4 style='color: white; margin-top: 0;'>🎯 Content Strategy</h4>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                if tag_counts:
                                    top_tags = [tag for tag, _ in tag_counts.most_common(3)]
                                    st.success(f"🏷️ **Hot tags:** {', '.join(top_tags)}")
                                
                                high_engagement_videos = [v for v in trend_data if v['engagement'] > avg_engagement]
                                st.info(f"🔥 **{len(high_engagement_videos)} videos** have above-average engagement")
                                
                                st.warning(f"📊 **Target engagement:** >{avg_engagement:.2f}% for best performance")
                            
                            # === QUICK TITLE GENERATOR ===
                            st.markdown("---")
                            st.markdown("### ✨ Quick Trend-Based Title Generator")
                            
                            if st.button("🎲 Generate Trending Title Ideas", type="primary"):
                                top_keyword = word_counts.most_common(1)[0][0] if word_counts else niche
                                top_emoji = emoji_counts.most_common(1)[0][0] if emoji_counts else random.choice(VIRAL_EMOJIS)
                                power_word = random.choice(POWER_WORDS_DB).upper()
                                number = random.choice(['5', '7', '10'])
                                year = datetime.datetime.now().year
                                
                                trend_titles = [
                                    f"{top_emoji} {number} {top_keyword.title()} {power_word} in {niche.title()} ({year})",
                                    f"How to {top_keyword.title()}: {power_word} {niche.title()} Guide {year} {top_emoji}",
                                    f"{power_word} {niche.title()} {top_keyword.title()} | {year} Tutorial {top_emoji}",
                                    f"{top_keyword.title()} {niche.title()} - {power_word} Tips {year} {top_emoji}"
                                ]
                                
                                st.markdown("**🎯 Based on current trends:**")
                                for title in trend_titles:
                                    st.code(title, language='text')
                        
                        else:
                            st.warning("No detailed stats available")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.caption("Please check your API key and try again")

# FOOTER
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: white; padding: 1.5rem;'>
    <p style='font-size: 1.1rem; font-weight: bold;'>🚀 YouTube VidIQ Clone</p>
    <p style='font-size: 0.9rem; opacity: 0.8;'>Advanced SEO & Analytics Tool | Powered by Sabrani</p>
    <p style='font-size: 0.8rem; opacity: 0.6;'>Made with ❤️ for Content Creators</p>
</div>
""", unsafe_allow_html=True)

