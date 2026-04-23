import json
import logging
from datetime import datetime, date, timedelta

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app

from app.dashboard import dashboard_bp
from app import db
from app.models import Update, Post, Source, ScheduledPost, CollectionLog, DailyStat
from config import Config as AppConfig

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────

def _bump_stat(field: str, delta: int = 1):
    today = date.today()
    stat = DailyStat.query.filter_by(date=today).first()
    if not stat:
        stat = DailyStat(date=today)
        db.session.add(stat)
    setattr(stat, field, getattr(stat, field) + delta)
    db.session.commit()


# ── Dashboard home ────────────────────────────────────────────────────────

@dashboard_bp.route("/")
def index():
    today = date.today()
    total_updates = Update.query.count()
    today_updates = Update.query.filter(db.func.date(Update.collected_at) == today).count()
    total_posts = Post.query.count()
    scheduled_count = ScheduledPost.query.filter_by(status="pending").count()
    published_count = Post.query.filter_by(status="posted").count()

    recent_updates = (
        Update.query.order_by(Update.collected_at.desc()).limit(10).all()
    )
    upcoming_posts = (
        ScheduledPost.query
        .filter_by(status="pending")
        .order_by(ScheduledPost.scheduled_at)
        .limit(5).all()
    )
    recent_logs = CollectionLog.query.order_by(CollectionLog.ran_at.desc()).limit(8).all()

    # Chart data: posts per day last 7 days
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        stat = DailyStat.query.filter_by(date=d).first()
        chart_labels.append(d.strftime("%b %d"))
        chart_data.append(stat.posts_published if stat else 0)

    return render_template(
        "index.html",
        total_updates=total_updates,
        today_updates=today_updates,
        total_posts=total_posts,
        scheduled_count=scheduled_count,
        published_count=published_count,
        recent_updates=recent_updates,
        upcoming_posts=upcoming_posts,
        recent_logs=recent_logs,
        chart_labels=json.dumps(chart_labels),
        chart_data=json.dumps(chart_data),
    )


# ── Updates ───────────────────────────────────────────────────────────────

@dashboard_bp.route("/updates")
def updates():
    page = request.args.get("page", 1, type=int)
    source_filter = request.args.get("source", "")
    category_filter = request.args.get("category", "")
    type_filter = request.args.get("type", "")
    starred_only = request.args.get("starred", "") == "1"

    q = Update.query.order_by(Update.collected_at.desc())
    if source_filter:
        q = q.join(Source).filter(Source.source_type == source_filter)
    if category_filter:
        q = q.filter(Update.category == category_filter)
    if type_filter:
        q = q.filter(Update.content_type == type_filter)
    if starred_only:
        q = q.filter(Update.is_starred == True)

    pagination = q.paginate(page=page, per_page=20)
    sources = Source.query.filter_by(is_active=True).all()
    return render_template("updates.html", pagination=pagination, sources=sources,
                           source_filter=source_filter, category_filter=category_filter,
                           type_filter=type_filter, starred_only=starred_only)


@dashboard_bp.route("/updates/<int:uid>/star", methods=["POST"])
def star_update(uid):
    update = Update.query.get_or_404(uid)
    update.is_starred = not update.is_starred
    db.session.commit()
    return jsonify({"starred": update.is_starred})


@dashboard_bp.route("/updates/<int:uid>/promote", methods=["POST"])
def promote_update(uid):
    update = Update.query.get_or_404(uid)
    from app.processors.content_generator import ContentGenerator
    gen = ContentGenerator(AppConfig)
    post = gen.process_update(update)
    if post:
        db.session.add(post)
        update.is_queued = True
        db.session.commit()
        _bump_stat("posts_created")
        flash(f"Draft post created from update #{uid}", "success")
        return redirect(url_for("dashboard.edit_post", pid=post.id))
    else:
        flash("Update scored too low for auto-processing. You can create a manual post.", "warning")
        return redirect(url_for("dashboard.updates"))


# ── Posts ─────────────────────────────────────────────────────────────────

@dashboard_bp.route("/posts")
def posts():
    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "")
    q = Post.query.order_by(Post.created_at.desc())
    if status_filter:
        q = q.filter(Post.status == status_filter)
    pagination = q.paginate(page=page, per_page=20)
    return render_template("posts.html", pagination=pagination, status_filter=status_filter)


@dashboard_bp.route("/posts/new", methods=["GET", "POST"])
def new_post():
    if request.method == "POST":
        caption = request.form.get("caption", "")
        hashtags_raw = request.form.get("hashtags", "")
        post_type = request.form.get("post_type", "feed")
        hashtags = [h.strip() for h in hashtags_raw.split() if h.strip()]
        post = Post(caption=caption, post_type=post_type, status="draft")
        post.hashtags = hashtags
        db.session.add(post)
        db.session.commit()
        _bump_stat("posts_created")
        flash("Manual post created!", "success")
        return redirect(url_for("dashboard.edit_post", pid=post.id))
    return render_template("content_editor.html", post=None, update=None)


@dashboard_bp.route("/posts/<int:pid>")
def edit_post(pid):
    post = Post.query.get_or_404(pid)
    update = post.update if post.update_id else None
    return render_template("content_editor.html", post=post, update=update)


@dashboard_bp.route("/posts/<int:pid>/save", methods=["POST"])
def save_post(pid):
    post = Post.query.get_or_404(pid)
    post.caption = request.form.get("caption", post.caption)
    hashtags_raw = request.form.get("hashtags", "")
    post.hashtags = [h.strip() for h in hashtags_raw.split() if h.strip()]
    post.editor_notes = request.form.get("editor_notes", "")
    post.updated_at = datetime.utcnow()
    db.session.commit()
    flash("Post saved!", "success")
    return redirect(url_for("dashboard.edit_post", pid=pid))


@dashboard_bp.route("/posts/<int:pid>/regenerate-caption", methods=["POST"])
def regenerate_caption(pid):
    post = Post.query.get_or_404(pid)
    if not post.update_id:
        return jsonify({"error": "No source update linked"}), 400
    from app.processors.caption_ai import CaptionAI
    ai = CaptionAI(AppConfig)
    result = ai.generate_caption(post.update, post.post_type)
    post.caption = result["caption"]
    post.hashtags = result["hashtags"]
    post.ai_caption_used = True
    post.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"caption": post.caption, "hashtags": post.hashtags})


@dashboard_bp.route("/posts/<int:pid>/regenerate-image", methods=["POST"])
def regenerate_image(pid):
    post = Post.query.get_or_404(pid)
    if not post.update_id:
        return jsonify({"error": "No source update linked"}), 400
    from app.processors.image_creator import ImageCreator
    creator = ImageCreator(AppConfig)
    post_type = request.form.get("post_type", "feed")
    if post_type == "story":
        path = creator.create_story_image(post.update, post.template_name)
    else:
        path = creator.create_post_image(post.update, post.template_name)
    post.image_path = path
    post.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"image_path": path, "image_url": f"/static/{path}"})


@dashboard_bp.route("/posts/<int:pid>/schedule", methods=["POST"])
def schedule_post(pid):
    post = Post.query.get_or_404(pid)
    from app.instagram.post_scheduler import PostScheduler
    sched = PostScheduler(AppConfig)
    scheduled_at_str = request.form.get("scheduled_at", "")
    if scheduled_at_str:
        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_str)
        except ValueError:
            scheduled_at = None
    else:
        scheduled_at = None
    sched.queue_post(post, scheduled_at)
    flash(f"Post scheduled for {post.scheduled_posts[-1].scheduled_at.strftime('%b %d, %Y %I:%M %p')} IST", "success")
    return redirect(url_for("dashboard.edit_post", pid=pid))


@dashboard_bp.route("/posts/<int:pid>/post-now", methods=["POST"])
def post_now(pid):
    post = Post.query.get_or_404(pid)
    from app.instagram.poster import InstagramPoster
    poster = InstagramPoster(AppConfig)
    try:
        ig_id = poster.post_feed_image(post)
        post.status = "posted"
        post.instagram_post_id = ig_id
        db.session.commit()
        _bump_stat("posts_published")
        flash(f"Posted to Instagram! ID: {ig_id}", "success")
    except Exception as e:
        flash(f"Posting failed: {e}", "danger")
    return redirect(url_for("dashboard.edit_post", pid=pid))


@dashboard_bp.route("/posts/<int:pid>/delete", methods=["POST"])
def delete_post(pid):
    post = Post.query.get_or_404(pid)
    db.session.delete(post)
    db.session.commit()
    flash("Post deleted.", "info")
    return redirect(url_for("dashboard.posts"))


# ── Scheduler ─────────────────────────────────────────────────────────────

@dashboard_bp.route("/scheduler")
def scheduler_view():
    upcoming = (
        ScheduledPost.query
        .filter(ScheduledPost.status.in_(["pending", "posting"]))
        .order_by(ScheduledPost.scheduled_at)
        .all()
    )
    recent_done = (
        ScheduledPost.query
        .filter(ScheduledPost.status.in_(["done", "failed"]))
        .order_by(ScheduledPost.posted_at.desc())
        .limit(20).all()
    )
    return render_template("scheduler_view.html", upcoming=upcoming, recent_done=recent_done)


@dashboard_bp.route("/scheduler/<int:sid>/cancel", methods=["POST"])
def cancel_scheduled(sid):
    sp = ScheduledPost.query.get_or_404(sid)
    sp.post.status = "draft"
    db.session.delete(sp)
    db.session.commit()
    flash("Scheduled post cancelled.", "info")
    return redirect(url_for("dashboard.scheduler_view"))


# ── Settings ──────────────────────────────────────────────────────────────

@dashboard_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "add_source":
            name = request.form.get("name", "").strip()
            source_type = request.form.get("source_type", "").strip()
            identifier = request.form.get("identifier", "").strip()
            if name and source_type and identifier:
                src = Source(name=name, source_type=source_type, identifier=identifier)
                db.session.add(src)
                db.session.commit()
                flash(f"Source '{name}' added!", "success")
            else:
                flash("All fields required.", "danger")
        elif action == "toggle_source":
            src_id = request.form.get("source_id", type=int)
            src = Source.query.get(src_id)
            if src:
                src.is_active = not src.is_active
                db.session.commit()
                flash(f"Source '{src.name}' {'enabled' if src.is_active else 'disabled'}.", "info")
        elif action == "delete_source":
            src_id = request.form.get("source_id", type=int)
            src = Source.query.get(src_id)
            if src:
                db.session.delete(src)
                db.session.commit()
                flash(f"Source deleted.", "info")
        return redirect(url_for("dashboard.settings"))

    sources = Source.query.order_by(Source.source_type, Source.name).all()

    # API connection status checks
    api_status = _check_api_status()

    return render_template("settings.html", sources=sources, api_status=api_status)


def _check_api_status() -> dict:
    cfg = current_app.config
    status = {}
    status["youtube"] = bool(cfg.get("YOUTUBE_API_KEY"))
    status["telegram"] = bool(cfg.get("TELEGRAM_API_ID") and cfg.get("TELEGRAM_API_HASH"))
    status["twitter"] = bool(cfg.get("TWITTER_BEARER_TOKEN"))
    status["anthropic"] = bool(cfg.get("ANTHROPIC_API_KEY"))
    ig_user = cfg.get("INSTAGRAM_USERNAME") or cfg.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    status["instagram"] = bool(ig_user)
    return status


# ── API endpoints ─────────────────────────────────────────────────────────

@dashboard_bp.route("/api/collect-now", methods=["POST"])
def api_collect_now():
    try:
        from app.collectors import get_collector_for_source
        from app.processors.content_generator import ContentGenerator
        sources = Source.query.filter_by(is_active=True).all()
        gen = ContentGenerator(AppConfig)
        total = 0
        source_results = []
        for source in sources:
            try:
                collector = get_collector_for_source(source, AppConfig)
                raw_items = collector.collect()
                saved = collector.save_updates(db.session, raw_items)
                source.last_checked_at = datetime.utcnow()
                new_updates = (
                    Update.query
                    .filter_by(source_id=source.id, is_processed=False)
                    .all()
                )
                for upd in new_updates:
                    post = gen.process_update(upd)
                    if post:
                        db.session.add(post)
                        _bump_stat("posts_created")
                db.session.commit()
                _bump_stat("updates_collected", saved)
                total += saved
                source_results.append({"name": source.name, "type": source.source_type, "saved": saved})
            except Exception as e:
                logger.error(f"Collection error for {source.name}: {e}")
                source_results.append({"name": source.name, "type": source.source_type, "saved": 0, "error": str(e)})
        return jsonify({"ok": True, "collected": total, "sources": source_results})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@dashboard_bp.route("/api/debug-sources")
def api_debug_sources():
    """Quick check: which sources are active and what type they are."""
    sources = Source.query.filter_by(is_active=True).all()
    result = []
    for s in sources:
        entry = {
            "id": s.id,
            "name": s.name,
            "type": s.source_type,
            "identifier": s.identifier,
            "last_checked_at": s.last_checked_at.isoformat() if s.last_checked_at else None,
        }
        if s.source_type == "youtube":
            entry["ready"] = bool(AppConfig.YOUTUBE_API_KEY)
            entry["note"] = "YouTube API key " + ("set" if AppConfig.YOUTUBE_API_KEY else "MISSING")
        elif s.source_type == "telegram":
            entry["ready"] = bool(AppConfig.TELEGRAM_API_ID and AppConfig.TELEGRAM_API_HASH)
            entry["note"] = "Telegram creds " + ("set" if entry["ready"] else "MISSING")
        else:
            entry["ready"] = True
            entry["note"] = "No API key needed"
        result.append(entry)
    return jsonify(result)


@dashboard_bp.route("/api/reset-sources", methods=["POST"])
def api_reset_sources():
    """Clear last_checked_at on all sources so next collect fetches recent items."""
    sources = Source.query.all()
    for s in sources:
        s.last_checked_at = None
    db.session.commit()
    return jsonify({"ok": True, "reset": len(sources)})


@dashboard_bp.route("/api/purge-spam", methods=["POST"])
def api_purge_spam():
    """Delete spam updates and their generated posts."""
    spam_phrases = [
        "FREE COURSE ALERT", "Join Now", "Enroll Now", "Limited Seats",
        "Offer Expires", "Registration Open", "New Batch Starting",
        "Batch Starting", "Admission Open", "Pay Now", "Buy Now",
    ]
    from app.models import Post
    deleted = 0
    for phrase in spam_phrases:
        matches = Update.query.filter(Update.title.ilike(f"%{phrase}%")).all()
        for u in matches:
            Post.query.filter_by(update_id=u.id).delete()
            db.session.delete(u)
            deleted += 1
    db.session.commit()
    return jsonify({"ok": True, "deleted": deleted})


@dashboard_bp.route("/api/reseed-sources", methods=["POST"])
def api_reseed_sources():
    """Add any missing default sources without touching existing ones."""
    from app.models import Source
    from app import ALL_DEFAULT_SOURCES
    existing_names = {s.name for s in Source.query.all()}
    added = []
    for name, stype, ident in ALL_DEFAULT_SOURCES:
        if name not in existing_names:
            db.session.add(Source(name=name, source_type=stype, identifier=ident))
            added.append(name)
    db.session.commit()
    return jsonify({"ok": True, "added": added, "count": len(added)})


@dashboard_bp.route("/api/stats")
def api_stats():
    today = date.today()
    stats = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        s = DailyStat.query.filter_by(date=d).first()
        stats.append(s.to_dict() if s else {"date": d.isoformat(), "updates_collected": 0,
                                              "posts_created": 0, "posts_published": 0})
    return jsonify(stats)


@dashboard_bp.route("/api/updates/feed")
def api_updates_feed():
    updates = Update.query.order_by(Update.collected_at.desc()).limit(10).all()
    return jsonify([u.to_dict() for u in updates])
