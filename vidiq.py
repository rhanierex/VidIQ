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
st.set_page_config(page_title="YouTube Master V24 PRO", page_icon="🚀", layout="wide")

# --- 2. DATABASE CONFIG ---
URL_DATABASE_ONLINE = "https://gist.githubusercontent.com/rhanierex/f2d76f11df8d550376d81b58124d3668/raw/0b58a1eb02a7cffc2261a1c8d353551f3337001c/gistfile1.txt"
FALLBACK_POWER_WORDS = ["secret", "best", "exposed", "tutorial", "guide", "how to", "tips", "tricks", "hacks", "ultimate", "complete", "full", "master", "proven", "amazing", "incredible"]
VIRAL_EMOJIS = ["🔥", "😱", "🔴", "✅", "❌", "🎵", "⚠️", "⚡", "🚀", "💰", "💯", "🤯", "😭", "😡", "😴", "🌙", "✨", "💤", "🌧️", "🎹", "👀", "💪", "🎯", "⭐", "🏆"]
STOP_WORDS = ["the", "and", "or", "for", "to", "in", "on", "at", "by", "with", "a", "an", "is", "it", "of", "that", "this", "video", "i", "you", "me", "we"]

# --- 3. LOAD DATA ---
@st.cache_data(ttl=600) 
def load_power_words(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list) and len(data) > 0: 
                    return data, "🟢 Online"
            except Exception:
                pass
    except Exception:
        pass
    return FALLBACK_POWER_WORDS, "🟠 Offline"

POWER_WORDS_DB, db_status = load_power_words(URL_DATABASE_ONLINE)

# --- 4. ADVANCED FUNCTIONS ---
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

def get_trending_tags(videos_data):
    """Extract trending tags from competitor videos"""
    all_tags = []
    for video in videos_data:
        if 'tags' in video:
            all_tags.extend(video['tags'])
    
    if not all_tags:
        return []
    
    tag_counts = Counter(all_tags)
    return [tag for tag, count in tag_counts.most_common(20)]

def analyze_best_upload_time(videos_data):
    """Analyze best time to upload based on competitors"""
    upload_hours = []
    for video in videos_data:
        try:
            published = video.get('publishedAt', '')
            hour = int(published[11:13])
            upload_hours.append(hour)
        except:
            continue
    
    if not upload_hours:
        return "Unknown"
    
    most_common_hour = Counter(upload_hours).most_common(1)[0][0]
    return f"{most_common_hour:02d}:00 - {(most_common_hour+1):02d}:00"

def calculate_keyword_score(keyword, search_volume, competition):
    """Calculate keyword opportunity score (0-100)"""
    try:
        # Higher search volume = better (max at 1M views)
        volume_score = min((search_volume / 1000000) * 50, 50)
        
        # Lower competition = better
        comp_score = 50 - (competition / 1000000) * 50
        comp_score = max(0, min(50, comp_score))
        
        total_score = volume_score + comp_score
        return int(total_score)
    except:
        return 50

def smart_truncate(text, max_length):
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_length: 
        return text
    truncated = text[:max_length-3]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."

def clean_title_text(title, keyword):
    if not keyword or not title: 
        return title
    try:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        clean = pattern.sub("", title).strip()
        clean = re.sub(r'^[:\-\|]\s*', '', clean)
        return clean
    except Exception:
        return title

def generate_tags(title, keyword, competitor_tags=None):
    if not title:
        return [keyword.lower()] if keyword else []
    
    try:
        clean_t = re.sub(r'[^\w\s]', '', title.lower())
        words = clean_t.split()
        tags = [keyword.lower()] if keyword else []
        year = datetime.datetime.now().year
        
        # Add words from title
        for w in words:
            if w not in STOP_WORDS and w not in tags and len(w) > 2:
                tags.append(w)
                if len(tags) >= 10:
                    break
        
        # Add trending tags from competitors
        if competitor_tags:
            for tag in competitor_tags[:5]:
                if tag.lower() not in tags and len(tags) < 15:
                    tags.append(tag.lower())
        
        # Add year-based tags
        if keyword:
            tags.append(f"{keyword.lower()} {year}")
            tags.append(f"{keyword.lower()} tutorial")
        
        return tags[:20]
    except Exception:
        return [keyword.lower()] if keyword else []

def generate_description(title, keyword, tags, video_length="10:00"):
    try:
        year = datetime.datetime.now().year
        tag_text = tags[1] if len(tags) > 1 else 'Viral'
        
        return f"""🔴 **{title}**

In this {video_length} video, we explore everything about **{keyword}**. Complete guide for {year}.

👇 **Timestamps:**
0:00 Introduction to {keyword}
0:30 Main Content
{int(video_length.split(':')[0])-2}:00 Key Takeaways
{int(video_length.split(':')[0])-1}:00 Conclusion & Next Steps

📚 **Resources Mentioned:**
• Link 1: [Coming Soon]
• Link 2: [Coming Soon]

🔔 **SUBSCRIBE for more {keyword} content!**

🏷️ **Related Topics:**
{', '.join(tags[:5])}

#Hashtags:
#{keyword.replace(" ", "")} #{tag_text} #{year} #Tutorial #HowTo

---
💬 Drop your questions in the comments!
👍 Like if this helped you!
🔔 Turn on notifications for new videos!

© {year} | All Rights Reserved"""
    except Exception:
        return "Video description here."

def generate_smart_suggestions(original_title, keyword, api_key=None, competitor_data=None):
    suggestions = []
    year = datetime.datetime.now().year
    
    # Analyze competitor titles
    power_word = random.choice(POWER_WORDS_DB).upper()
    emoji = random.choice(VIRAL_EMOJIS)
    
    if competitor_data and len(competitor_data) > 0:
        # Extract patterns from top video
        top_title = competitor_data[0].get('title', '')
        
        # Find numbers in top titles
        numbers = re.findall(r'\d+', top_title)
        if numbers:
            number = numbers[0]
        else:
            number = random.choice(['5', '7', '10', '15'])
        
        # Find power words in top titles
        for word in POWER_WORDS_DB:
            if word.lower() in top_title.lower():
                power_word = word.upper()
                break
    else:
        number = random.choice(['5', '7', '10'])
    
    core = clean_title_text(original_title, keyword) if keyword else original_title
    if not core or core.strip() == "":
        core = "Complete Guide"
    
    try:
        # Formula 1: Number-based (Like VidIQ)
        sug1 = f"{emoji} {number} {keyword.title()} {power_word} You NEED to Know ({year})"
        suggestions.append(sug1)

        # Formula 2: Question-based
        sug2 = f"How to {keyword.title()}: {power_word} Guide for {year} {emoji}"
        suggestions.append(sug2)
        
        # Formula 3: Urgency-based
        sug3 = f"{keyword.title()} Tutorial - {power_word} Strategy {year} {emoji}"
        suggestions.append(sug3)
        
        # Formula 4: Benefit-focused
        sug4 = f"{core} | {keyword.title()} {power_word} Tips [{year}] {emoji}"
        suggestions.append(sug4)
        
    except Exception:
        suggestions.append(f"{keyword.title()} - {core} {emoji}")
    
    return suggestions[:4]

def analyze_title(title, keyword=""):
    score = 0
    checks = []
    
    if not title:
        return 0, [("error", "Title is empty")]
    
    try:
        # Length check (VidIQ style)
        title_len = len(title)
        if 40 <= title_len <= 70: 
            score += 25
            checks.append(("success", f"✅ Perfect Length ({title_len}/100) - Sweet spot!"))
        elif 30 <= title_len <= 90: 
            score += 20
            checks.append(("warning", f"⚠️ Good Length ({title_len}/100) - Can improve"))
        elif title_len < 30:
            score += 10
            checks.append(("error", f"❌ Too Short ({title_len}/100) - Add more context"))
        else: 
            score += 5
            checks.append(("error", f"❌ Too Long ({title_len}/100) - Will be cut off"))

        # Keyword check
        if keyword:
            if keyword.lower() in title.lower():
                title_start = re.sub(r'^[^a-zA-Z0-9]+', '', title.lower()).strip()
                if title_start.startswith(keyword.lower()):
                    score += 20
                    checks.append(("success", "✅ Keyword at Start - Perfect for SEO!"))
                else: 
                    score += 15
                    checks.append(("warning", "⚠️ Keyword Present - Move to start for better SEO"))
            else: 
                checks.append(("error", "❌ Keyword Missing - Critical for ranking!"))
        else: 
            score += 20

        # Power word check
        found_power_words = [pw for pw in POWER_WORDS_DB if pw.lower() in title.lower()]
        if found_power_words: 
            score += 15
            checks.append(("success", f"✅ Power Words Found: {', '.join(found_power_words[:3])}"))
        else: 
            checks.append(("warning", "⚠️ No Power Words - Add words like 'BEST', 'ULTIMATE', 'SECRET'"))
        
        # Number check
        numbers = re.findall(r'\d+', title)
        if numbers: 
            score += 15
            checks.append(("success", f"✅ Numbers Used: {', '.join(numbers)} - Increases CTR by 36%"))
        else: 
            checks.append(("info", "💡 Add Numbers - Titles with numbers get 36% more clicks"))
        
        # Emoji check
        emojis_found = [e for e in VIRAL_EMOJIS if e in title]
        if emojis_found: 
            score += 10
            checks.append(("success", f"✅ Emoji Used: {' '.join(emojis_found)} - Catches attention"))
        else: 
            checks.append(("info", "💡 Add Emoji - Increases visibility in search"))
        
        # Caps check (all caps is bad)
        if title.isupper():
            score -= 10
            checks.append(("error", "❌ ALL CAPS - Looks spammy, use mixed case"))
        
        # Question mark (engaging)
        if '?' in title:
            score += 5
            checks.append(("success", "✅ Question Format - Creates curiosity"))
        
        # Brackets/Parentheses (proven to work)
        if '[' in title or '(' in title:
            score += 5
            checks.append(("success", "✅ Brackets Used - Adds context & increases CTR"))
        
        return min(score, 100), checks
    except Exception as e:
        return 0, [("error", f"Analysis error: {str(e)}")]

def get_keyword_metrics(api_key, keyword):
    """Enhanced keyword analysis like VidIQ"""
    if not api_key or api_key.strip() == "": 
        return None, "❌ API Key kosong"
    
    if len(api_key) < 30:
        return None, "❌ API Key tidak valid"
    
    if not keyword or keyword.strip() == "":
        return None, "❌ Keyword kosong"
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Search videos
        search_res = youtube.search().list(
            q=keyword, 
            type='video', 
            part='id,snippet', 
            maxResults=20,  # Increased for better analysis
            order='relevance',
            regionCode='ID'
        ).execute()
        
        if 'items' not in search_res or len(search_res['items']) == 0:
            return None, f"❌ Tidak ada video untuk '{keyword}'"
        
        # Extract video IDs
        video_ids = [item['id']['videoId'] for item in search_res['items'] if 'videoId' in item.get('id', {})]
        
        if not video_ids:
            return None, "❌ Tidak bisa mengambil video ID"
        
        # Get detailed video statistics
        stats_res = youtube.videos().list(
            id=','.join(video_ids), 
            part='statistics,snippet,contentDetails'
        ).execute()
        
        if not stats_res or 'items' not in stats_res:
            return None, "❌ Gagal mengambil statistik"
        
        # Process metrics
        metrics = []
        all_tags = []
        upload_times = []
        
        for item in stats_res['items']:
            try:
                snippet = item.get('snippet', {})
                stats = item.get('statistics', {})
                
                views = int(stats.get('viewCount', 0))
                likes = int(stats.get('likeCount', 0))
                comments = int(stats.get('commentCount', 0))
                
                engagement = calculate_engagement_rate(stats)
                
                # Extract tags
                tags = snippet.get('tags', [])
                all_tags.extend(tags)
                
                # Upload time
                published = snippet.get('publishedAt', '')
                if published:
                    upload_times.append(published)
                
                metrics.append({
                    'Title': snippet.get('title', 'Unknown'),
                    'Views': views,
                    'Likes': likes,
                    'Comments': comments,
                    'Engagement': engagement,
                    'Channel': snippet.get('channelTitle', 'Unknown'),
                    'Date': published[:10],
                    'tags': tags,
                    'publishedAt': published
                })
            except Exception:
                continue
        
        if not metrics:
            return None, "❌ Gagal memproses data"
        
        # Create DataFrame
        df = pd.DataFrame(metrics)
        
        # Calculate comprehensive metrics
        view_counts = [m['Views'] for m in metrics if m['Views'] > 0]
        engagement_rates = [m['Engagement'] for m in metrics if m['Engagement'] > 0]
        
        median_views = statistics.median(view_counts) if view_counts else 0
        avg_views = statistics.mean(view_counts) if view_counts else 0
        avg_engagement = statistics.mean(engagement_rates) if engagement_rates else 0
        
        # Trending tags
        trending_tags = []
        if all_tags:
            tag_counts = Counter(all_tags)
            trending_tags = [tag for tag, count in tag_counts.most_common(15)]
        
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
        
        # Opportunity score (like VidIQ)
        opportunity_score = calculate_keyword_score(keyword, median_views, median_views)
        
        result = {
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
        }
        
        return result, None
        
    except Exception as e:
        error_msg = str(e)
        if "API key not valid" in error_msg:
            return None, "❌ API Key tidak valid!"
        elif "quota" in error_msg.lower():
            return None, "❌ Quota API habis!"
        else:
            return None, f"❌ Error: {error_msg}"

# --- 5. VISUALIZATION ---
def draw_safe_chart(df):
    if df is None or df.empty:
        st.warning("No data to display")
        return
    
    try:
        st.markdown("### 📊 Top Competitor Analysis")
        max_views = df['Views'].max()
        
        if max_views == 0:
            max_views = 1
        
        for index, row in df.head(10).iterrows():
            title = row['Title']
            if len(title) > 50:
                title = title[:50] + "..."
            
            views = row['Views']
            engagement = row.get('Engagement', 0)
            width_pct = int((views / max_views) * 100)
            
            # Color based on engagement
            if engagement > 5:
                bar_color = "#00ff00"
            elif engagement > 2:
                bar_color = "#ffa500"
            else:
                bar_color = "#ff4b4b"
            
            st.markdown(f"""
            <div style="margin-bottom: 15px; padding: 10px; background-color: #1e1e1e; border-radius: 8px;">
                <div style="font-size: 14px; font-weight: bold; color: #fff;">{title}</div>
                <div style="font-size: 12px; color: #aaa; margin: 5px 0;">
                    {row['Channel']} • {views:,} Views • {engagement}% Engagement
                </div>
                <div style="background-color: #333; width: 100%; height: 12px; border-radius: 6px; overflow: hidden;">
                    <div style="background-color: {bar_color}; width: {width_pct}%; height: 12px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error: {str(e)}")

def draw_engagement_chart(df):
    """Show engagement rate comparison"""
    try:
        st.markdown("### 📈 Engagement Rate Analysis")
        
        avg_engagement = df['Engagement'].mean()
        
        for index, row in df.head(5).iterrows():
            title = row['Title'][:40] + "..." if len(row['Title']) > 40 else row['Title']
            engagement = row['Engagement']
            
            # Compare to average
            if engagement > avg_engagement * 1.5:
                color = "#00ff00"
                label = "🔥 High"
            elif engagement > avg_engagement:
                color = "#ffa500"
                label = "📈 Above Avg"
            else:
                color = "#ff4b4b"
                label = "📉 Below Avg"
            
            width = min(int(engagement * 10), 100)
            
            st.markdown(f"""
            <div style="margin-bottom: 10px;">
                <div style="font-size: 13px; color: #fff;">{title}</div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="background-color: #333; width: 70%; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="background-color: {color}; width: {width}%; height: 8px;"></div>
                    </div>
                    <span style="color: {color}; font-size: 12px; font-weight: bold;">{engagement}% {label}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    except:
        pass

# --- 6. UI MAIN ---
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    if "Online" in db_status: 
        st.success(db_status)
    else: 
        st.warning(db_status)
    st.divider()
    
    st.markdown("### 🔑 YouTube API Key")
    api_key = st.text_input("API Key:", type="password", placeholder="AIzaSy...")
    
    if api_key and len(api_key) > 30: 
        st.success("🟢 Connected")
    elif api_key:
        st.warning("⚠️ Too short")
    
    with st.expander("📖 How to Get API Key"):
        st.markdown("""
        **Quick Steps:**
        
        1. Visit [Google Cloud Console](https://console.cloud.google.com)
        2. Create new project
        3. Enable "YouTube Data API v3"
        4. Create API Key
        5. Paste above ↑
        
        📊 **Free Quota:** 10,000 units/day
        """)

st.markdown("""
<h1 style='text-align: center;'>
    🚀 YouTube Master V24 PRO
</h1>
<p style='text-align: center; color: #888;'>
    Advanced YouTube SEO & Analytics Tool - VidIQ Style
</p>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🔍 Keyword Research", "📝 Title Optimizer", "📺 Channel Audit", "🎯 Trend Finder"])

# TAB 1: KEYWORD RESEARCH (Enhanced)
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        kw_input = st.text_input("🔎 Enter Your Topic:", placeholder="e.g., lullaby sleeping music", key="kw1")
    with col2:
        st.write("")
        st.write("")
        analyze_btn = st.button("🚀 Deep Analysis", type="primary", use_container_width=True)
    
    if analyze_btn:
        if not api_key or len(api_key) < 30:
            st.error("⚠️ Please enter valid API Key in sidebar!")
        elif not kw_input:
            st.warning("⚠️ Enter a keyword first!")
        else:
            with st.spinner(f"🔍 Analyzing '{kw_input}'... This may take a moment"):
                data, err = get_keyword_metrics(api_key, kw_input)
                
                if err:
                    st.error(err)
                elif data:
                    st.success(f"✅ Analysis Complete for '{kw_input}'")
                    
                    # METRICS OVERVIEW
                    st.markdown("### 📊 Market Overview")
                    m1, m2, m3, m4 = st.columns(4)
                    
                    with m1:
                        st.metric(
                            "Opportunity Score",
                            f"{data['score']}/100",
                            delta="Good" if data['score'] > 60 else "Hard"
                        )
                    with m2:
                        st.metric(
                            "Competition",
                            data['difficulty'],
                            delta=f"{data['difficulty_score']}% Ease"
                        )
                    with m3:
                        st.metric(
                            "Avg Views",
                            f"{int(data['avg_views']):,}",
                            delta=f"{data['avg_engagement']:.1f}% Engage"
                        )
                    with m4:
                        st.metric(
                            "Videos Found",
                            data['total_videos'],
                            delta="Analyzed"
                        )
                    
                    st.divider()
                    
                    # INSIGHTS
                    col_left, col_right = st.columns([2, 1])
                    
                    with col_left:
                        draw_safe_chart(data['top_videos'])
                        
                        st.divider()
                        draw_engagement_chart(data['top_videos'])
                    
                    with col_right:
                        st.markdown("### 🏷️ Trending Tags")
                        if data['trending_tags']:
                            tags_html = "".join([f"<span style='background-color:#333;padding:4px 8px;margin:4px;border-radius:4px;display:inline-block;font-size:12px;'>{tag}</span>" for tag in data['trending_tags'][:12]])
                            st.markdown(tags_html, unsafe_allow_html=True)
                        else:
                            st.info("No tags found")
                        
                        st.divider()
                        
                        st.markdown("### ⏰ Best Upload Time")
                        st.info(f"🕐 **{data['best_upload_time']}**")
                        st.caption("Based on competitor analysis")
                        
                        st.divider()
                        
                        st.markdown("### 💡 Quick Tips")
                        if data['score'] > 70:
                            st.success("✅ Great keyword! Low competition, good volume")
                        elif data['score'] > 40:
                            st.warning("⚠️ Moderate difficulty. Create unique content to stand out")
                        else:
                            st.error("🔴 High competition. Consider long-tail keywords")
                    
                    # DETAILED TABLE
                    st.divider()
                    st.markdown("### 📋 Competitor Breakdown")
                    
                    display_df = data['top_videos'][['Title', 'Views', 'Likes', 'Comments', 'Engagement', 'Channel']].copy()
                    display_df['Views'] = display_df['Views'].apply(lambda x: f"{x:,}")
                    display_df['Likes'] = display_df['Likes'].apply(lambda x: f"{x:,}")
                    display_df['Engagement'] = display_df['Engagement'].apply(lambda x: f"{x}%")
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)

# TAB 2: TITLE OPTIMIZER (Enhanced)
with tab2:
    st.markdown("### ✍️ Optimize Your Video Title")
    
    col_kw, col_title = st.columns([1, 2])
    with col_kw:
        keyword = st.text_input("🎯 Main Keyword:", placeholder="e.g., relaxing jazz")
    with col_title:
        title = st.text_input("📝 Your Title:", placeholder="Paste or write your title here...")
    
    if st.button("🔍 Analyze & Optimize", type="primary"):
        if not title:
            st.warning("⚠️ Enter a title first!")
        else:
            score, logs = analyze_title(title, keyword)
            
            # SCORE DISPLAY
            if score >= 80:
                clr = "#00ff00"
                grade = "A"
                msg = "Excellent!"
            elif score >= 60:
                clr = "#ffa500"
                grade = "B"
                msg = "Good"
            else:
                clr = "#ff4b4b"
                grade = "C"
                msg = "Needs Work"
            
            col_score, col_grade = st.columns([3, 1])
            with col_score:
                st.markdown(f"""
                <div style='background: linear-gradient(90deg, {clr}20, transparent); padding: 20px; border-radius: 10px; border-left: 4px solid {clr};'>
                    <h2 style='color: {clr}; margin: 0;'>SEO Score: {score}/100</h2>
                    <p style='color: #aaa; margin: 5px 0 0 0;'>{msg} - Your title is {grade} grade</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_grade:
                st.markdown(f"<h1 style='color:{clr}; text-align: center; font-size: 60px; margin: 0;'>{grade}</h1>", unsafe_allow_html=True)
            
            st.divider()
            
            # DETAILED CHECKS
            col_checks, col_viz = st.columns([2, 1])
            
            with col_checks:
                st.markdown("### 📋 SEO Checklist")
                for status, message in logs:
                    if status == "success":
                        st.success(message, icon="✅")
                    elif status == "warning":
                        st.warning(message, icon="⚠️")
                    elif status == "info":
                        st.info(message, icon="💡")
                    else:
                        st.error(message, icon="❌")
            
            with col_viz:
                st.markdown("### 🎯 Score Breakdown")
                
                # Score components
                components = {
                    "Length": 25,
                    "Keyword": 20,
                    "Power Words": 15,
                    "Numbers": 15,
                    "Emoji": 10,
                    "Engagement": 15
                }
                
                for comp, max_score in components.items():
                    pct = min((score / 100) * max_score, max_score)
                    width = int((pct / max_score) * 100)
                    
                    st.markdown(f"""
                    <div style="margin-bottom: 8px;">
                        <div style="font-size: 11px; color: #aaa;">{comp} ({int(pct)}/{max_score})</div>
                        <div style="background-color: #333; height: 6px; border-radius: 3px; overflow: hidden;">
                            <div style="background-color: {clr}; width: {width}%; height: 6px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # SUGGESTIONS
            if score < 85 and keyword:
                st.divider()
                st.markdown("### 💡 AI-Powered Suggestions (VidIQ Style)")
                
                # Get competitor data if API available
                competitor_data = None
                if api_key and len(api_key) > 30:
                    with st.spinner("Analyzing top competitors..."):
                        result, _ = get_keyword_metrics(api_key, keyword)
                        if result:
                            competitor_data = result.get('competitor_data', [])
                
                suggestions = generate_smart_suggestions(title, keyword, api_key, competitor_data)
                
                for i, sug in enumerate(suggestions, 1):
                    sug_score, _ = analyze_title(sug, keyword)
                    
                    if sug_score > score:
                        badge = "🔥 Better"
                        badge_color = "#00ff00"
                    else:
                        badge = "📝 Alternative"
                        badge_color = "#ffa500"
                    
                    st.markdown(f"""
                    <div style='background-color: #1e1e1e; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid {badge_color};'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <span style='color: {badge_color}; font-weight: bold; font-size: 12px;'>{badge}</span>
                            <span style='color: {badge_color}; font-weight: bold;'>Score: {sug_score}/100</span>
                        </div>
                        <p style='color: #fff; margin: 10px 0; font-size: 14px;'>{sug}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"📋 Copy #{i}", key=f"copy_{i}"):
                        st.code(sug, language='text')
            
            # TAGS & DESCRIPTION
            st.divider()
            col_tags, col_desc = st.columns(2)
            
            # Get trending tags if API available
            trending_tags = []
            if api_key and len(api_key) > 30 and keyword:
                with st.spinner("Getting trending tags..."):
                    result, _ = get_keyword_metrics(api_key, keyword)
                    if result:
                        trending_tags = result.get('trending_tags', [])
            
            generated_tags = generate_tags(title, keyword, trending_tags)
            
            with col_tags:
                st.markdown("### 🏷️ Optimized Tags")
                st.text_area(
                    "Tags (comma separated):",
                    ", ".join(generated_tags),
                    height=200,
                    help="Copy and paste into YouTube"
                )
                st.caption(f"✅ {len(generated_tags)} tags generated")
            
            with col_desc:
                st.markdown("### 📄 SEO Description")
                description = generate_description(title, keyword, generated_tags)
                st.text_area(
                    "Description:",
                    description,
                    height=200,
                    help="Optimized for YouTube SEO"
                )
                st.caption("✅ Includes timestamps, hashtags & CTAs")

# TAB 3: CHANNEL AUDIT
with tab3:
    st.markdown("### 📺 Channel Performance Audit")
    
    col_id, col_btn = st.columns([3, 1])
    with col_id:
        channel_id = st.text_input("Channel ID (UC...):", placeholder="e.g., UC_x5XG1OV2P6uZZ5FSM9Ttw")
    with col_btn:
        st.write("")
        st.write("")
        audit_btn = st.button("🔍 Audit Channel", type="primary", use_container_width=True)
    
    if audit_btn:
        if not api_key or len(api_key) < 30:
            st.error("⚠️ API Key required")
        elif not channel_id or not channel_id.startswith("UC"):
            st.error("⚠️ Invalid Channel ID")
        else:
            with st.spinner("Auditing channel..."):
                try:
                    yt = build('youtube', 'v3', developerKey=api_key)
                    
                    # Get channel info
                    ch_res = yt.channels().list(
                        id=channel_id,
                        part='snippet,statistics,contentDetails,brandingSettings'
                    ).execute()
                    
                    if not ch_res.get('items'):
                        st.error("❌ Channel not found")
                    else:
                        ch = ch_res['items'][0]
                        snippet = ch['snippet']
                        stats = ch['statistics']
                        
                        # CHANNEL HEADER
                        st.markdown("---")
                        col_img, col_info, col_stats = st.columns([1, 3, 2])
                        
                        with col_img:
                            st.image(snippet['thumbnails']['medium']['url'], width=120)
                        
                        with col_info:
                            st.markdown(f"## {snippet['title']}")
                            st.caption(snippet.get('description', '')[:150] + "...")
                        
                        with col_stats:
                            subs = int(stats.get('subscriberCount', 0))
                            views = int(stats.get('viewCount', 0))
                            videos = int(stats.get('videoCount', 0))
                            
                            st.metric("Subscribers", f"{subs:,}")
                            st.metric("Total Views", f"{views:,}")
                            st.metric("Videos", f"{videos:,}")
                        
                        st.markdown("---")
                        
                        # Get recent videos
                        upload_id = ch['contentDetails']['relatedPlaylists']['uploads']
                        vids_res = yt.playlistItems().list(
                            playlistId=upload_id,
                            part='snippet',
                            maxResults=10
                        ).execute()
                        
                        st.markdown("### 📹 Recent Videos Analysis")
                        
                        total_score = 0
                        video_count = 0
                        
                        for item in vids_res.get('items', []):
                            vid_title = item['snippet']['title']
                            vid_thumb = item['snippet']['thumbnails']['default']['url']
                            vid_date = item['snippet']['publishedAt'][:10]
                            
                            # Extract keyword from title
                            kw = vid_title.split()[0] if vid_title else "video"
                            
                            # Analyze title
                            vid_score, checks = analyze_title(vid_title, kw)
                            total_score += vid_score
                            video_count += 1
                            
                            # Display video
                            with st.container():
                                col_a, col_b = st.columns([1, 5])
                                
                                with col_a:
                                    st.image(vid_thumb, width=120)
                                
                                with col_b:
                                    st.markdown(f"**{vid_title}**")
                                    st.caption(f"📅 {vid_date}")
                                    
                                    # Score indicator
                                    if vid_score >= 80:
                                        score_color = "#00ff00"
                                        score_label = "🔥 Excellent"
                                    elif vid_score >= 60:
                                        score_color = "#ffa500"
                                        score_label = "📈 Good"
                                    else:
                                        score_color = "#ff4b4b"
                                        score_label = "⚠️ Needs Work"
                                    
                                    st.markdown(f"<span style='color:{score_color}; font-weight:bold;'>SEO Score: {vid_score}/100 {score_label}</span>", unsafe_allow_html=True)
                                    
                                    if vid_score < 80:
                                        with st.expander("💡 See Improvements"):
                                            suggestions = generate_smart_suggestions(vid_title, kw, api_key)
                                            for sug in suggestions[:2]:
                                                st.code(sug, language='text')
                                
                                st.divider()
                        
                        # Channel summary
                        if video_count > 0:
                            avg_score = total_score / video_count
                            
                            st.markdown("### 📊 Channel SEO Summary")
                            
                            m1, m2, m3 = st.columns(3)
                            with m1:
                                st.metric("Average SEO Score", f"{int(avg_score)}/100")
                            with m2:
                                good_videos = sum(1 for item in vids_res.get('items', []) if analyze_title(item['snippet']['title'])[0] >= 70)
                                st.metric("Well-Optimized Videos", f"{good_videos}/{video_count}")
                            with m3:
                                improvement = 100 - avg_score
                                st.metric("Improvement Potential", f"+{int(improvement)}%")
                            
                            # Recommendations
                            st.markdown("### 💡 Channel Recommendations")
                            if avg_score >= 80:
                                st.success("✅ Your channel has excellent SEO! Keep up the great work.")
                            elif avg_score >= 60:
                                st.warning("⚠️ Good SEO but room for improvement. Focus on adding keywords and power words.")
                            else:
                                st.error("🔴 Your channel needs SEO optimization. Use our Title Optimizer for each video.")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# TAB 4: TREND FINDER
with tab4:
    st.markdown("### 🎯 Find Trending Topics in Your Niche")
    
    niche = st.text_input("Your Niche:", placeholder="e.g., gaming, cooking, music")
    
    if st.button("🔥 Find Trends", type="primary"):
        if not api_key or len(api_key) < 30:
            st.error("⚠️ API Key required")
        elif not niche:
            st.warning("⚠️ Enter your niche")
        else:
            with st.spinner(f"Finding trends in '{niche}'..."):
                try:
                    yt = build('youtube', 'v3', developerKey=api_key)
                    
                    # Search trending videos
                    trends_res = yt.search().list(
                        q=niche,
                        type='video',
                        part='id,snippet',
                        maxResults=15,
                        order='viewCount',
                        publishedAfter=(datetime.datetime.now() - datetime.timedelta(days=7)).isoformat() + 'Z'
                    ).execute()
                    
                    if trends_res.get('items'):
                        video_ids = [item['id']['videoId'] for item in trends_res['items'] if 'videoId' in item.get('id', {})]
                        
                        # Get stats
                        stats_res = yt.videos().list(
                            id=','.join(video_ids),
                            part='statistics,snippet'
                        ).execute()
                        
                        st.success(f"✅ Found {len(stats_res['items'])} trending videos this week")
                        
                        # Extract trending patterns
                        all_words = []
                        all_tags = []
                        
                        for item in stats_res['items']:
                            title = item['snippet']['title']
                            tags = item['snippet'].get('tags', [])
                            
                            # Extract words from title
                            words = re.findall(r'\b[a-zA-Z]{4,}\b', title.lower())
                            all_words.extend(words)
                            all_tags.extend(tags)
                        
                        # Find most common
                        word_counts = Counter([w for w in all_words if w not in STOP_WORDS])
                        tag_counts = Counter(all_tags)
                        
                        # Display insights
                        col_words, col_tags = st.columns(2)
                        
                        with col_words:
                            st.markdown("### 🔥 Trending Keywords")
                            for word, count in word_counts.most_common(10):
                                st.markdown(f"**{word.title()}** - Used {count} times")
                        
                        with col_tags:
                            st.markdown("### 🏷️ Hot Tags")
                            for tag, count in tag_counts.most_common(10):
                                st.markdown(f"#{tag} - {count} videos")
                        
                        st.divider()
                        
                        # Show trending videos
                        st.markdown("### 📈 Trending Videos (Last 7 Days)")
                        
                        for item in stats_res['items'][:5]:
                            with st.container():
                                col_a, col_b = st.columns([1, 4])
                                
                                with col_a:
                                    st.image(item['snippet']['thumbnails']['default']['url'])
                                
                                with col_b:
                                    st.markdown(f"**{item['snippet']['title']}**")
                                    views = int(item['statistics'].get('viewCount', 0))
                                    st.caption(f"👁️ {views:,} views • {item['snippet']['channelTitle']}")
                                
                                st.divider()
                    
                    else:
                        st.warning("No trending videos found. Try a different niche.")
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# FOOTER
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p><strong>YouTube Master V24 PRO</strong> - Advanced SEO & Analytics Tool</p>
    <p style='font-size: 12px;'>Made with ❤️ | Powered by YouTube Data API v3</p>
</div>
""", unsafe_allow_html=True)