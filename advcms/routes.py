
import re
import bcrypt
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse, HTMLResponse, RedirectResponse, PlainTextResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from advcms.utils import build_media_url, delete_uploaded_file, is_allowed_media_type, save_uploaded_file, slugify
from advcms.data import DBConnection

from advcms.templates import app_templates
from advcms.agents.root_agent import ADVCMSRootAgent

from advcms.agents.tools.chroma_tool import app_chromaconnector

db_session = DBConnection()
if db_session.connect() < 0:
    print("Failed to connect to the database. Exiting.")
    exit(1)

agent_manager = ADVCMSRootAgent()
if agent_manager is None:
    print("Failed to initialize the agent manager. Exiting.")
    exit(1)

async def home(request: StarletteRequest):
    posts = db_session.get_all_published_posts()
    return app_templates.TemplateResponse(request, "index.html", {"posts": posts})

def get_current_username(request: StarletteRequest)-> str:
    
    if request is not None:
        if request.user is not None:
            if request.user.is_authenticated: 
                return request.user.username
    
    return "guest"

async def login_get(request: StarletteRequest):
    if request.user.is_authenticated:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    message = request.session.pop("message", None)
    return app_templates.TemplateResponse(request, "login.html", {"message": message})

async def login_post(request: StarletteRequest):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")

    if not username or not password:
        return app_templates.TemplateResponse(
           request, "login.html", {"error": "All fields are required."}
        )

    user = db_session.get_user_by_username(username)
    if not user:
        return app_templates.TemplateResponse(
            request, "login.html", {"error": "Invalid username or password."}
        )

    hashed = user.password_hash.encode("utf-8")
    if not bcrypt.checkpw(password.encode("utf-8"), hashed):
        return app_templates.TemplateResponse(
            request, "login.html", {"error": "Invalid username or password."}
        )

    request.session["user"] = {"id": user.id, "username": user.username}
    return RedirectResponse(url="/dashboard", status_code=303)

async def register_get(request: StarletteRequest):
    if request.user.is_authenticated:
        return RedirectResponse(url="/dashboard", status_code=303)
    return app_templates.TemplateResponse(request, "register.html")

async def register_post(request: StarletteRequest):
    form = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")

    if not username or not password:
        return app_templates.TemplateResponse(
            request, "register.html", {"error": "All fields are required."}
        )

    if len(password) < 6:
        return app_templates.TemplateResponse(
            request, "register.html", {"error": "Password must be at least 6 characters."}
        )

    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    success = db_session.create_user(username, password_hash)
    if not success:
        return app_templates.TemplateResponse(
            request, "register.html", {"error": "Username already exists."}
        )

    request.session["message"] = "Registration successful! Please sign in."
    return RedirectResponse(url="/login", status_code=303)

async def dashboard(request: StarletteRequest):
    if not request.user.is_authenticated:
        return RedirectResponse(url="/login", status_code=303)
    posts = db_session.get_posts_by_author(request.user.id)
    return app_templates.TemplateResponse(request, "dashboard.html", {"posts": posts})

async def logout(request: StarletteRequest):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

async def post_detail(request: StarletteRequest):
    slug = request.path_params["slug"]
    post = db_session.get_post_by_slug(slug)
    if not post or (post.status != "published" and (not request.user.is_authenticated or request.user.id != post.author_id)):
        return PlainTextResponse("Post not found", status_code=404)
    return app_templates.TemplateResponse(request, "post_detail.html", {"post": post})

async def post_new_get(request: StarletteRequest):
    if not request.user.is_authenticated:
        return RedirectResponse(url="/login", status_code=303)
    return app_templates.TemplateResponse(request, "post_edit.html", {"action": "create", "post": None})

async def post_new_post(request: StarletteRequest):
    if not request.user.is_authenticated:
        return RedirectResponse(url="/login", status_code=303)
    form = await request.form()
    title = form.get("title", "").strip()
    category = form.get("category", "").strip()
    summary = form.get("summary", "").strip()
    content = form.get("content", "").strip()
    status = form.get("status", "draft").strip()
    media_url = None

    media_upload = form.get("media")
    remove_media = form.get("remove_media") == "1"
    if media_upload and getattr(media_upload, "filename", None):
        content_type = (getattr(media_upload, "content_type", "") or "").split(";", 1)[0].lower()
        if not is_allowed_media_type(content_type):
            return app_templates.TemplateResponse(
                request, "post_edit.html",
                {"action": "create", "post": None, "error": "Only image, video, audio, and PDF files are supported."}
            )
        file_bytes = await media_upload.read()
        saved_path = save_uploaded_file(file_bytes, media_upload.filename)
        if saved_path:
            media_url = build_media_url(saved_path)
    elif remove_media:
        media_url = None
    
    if not title or not content:
        return app_templates.TemplateResponse(
            request, "post_edit.html", 
            {"action": "create", "post": None, "error": "Title and Content are required."}
        )
    
    slug = slugify(title)
    base_slug = slug
    counter = 1

    while db_session.get_post_by_slug(slug) is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1

    success = db_session.create_post(title, slug, category, summary, content, status, request.user.id, media_url)
    if not success:
        return app_templates.TemplateResponse(
            request, "post_edit.html", 
            {"action": "create", "post": None, "error": "Failed to create post. Try a different title."}
        )
    else:
        username: str = get_current_username(request)
        await add_data_to_chroma(username, str(content), str(slug), str(category), str(title), str(summary))
        return RedirectResponse(url="/dashboard", status_code=303)

async def post_edit_get(request: StarletteRequest):
    if not request.user.is_authenticated:
        return RedirectResponse(url="/login", status_code=303)
    post_id = request.path_params["id"]
    post = db_session.get_post_by_id(post_id)
    if not post or post.author_id != request.user.id:
        return PlainTextResponse("Unauthorized or Post not found", status_code=404)
    return app_templates.TemplateResponse(request, "post_edit.html", {"action": "edit", "post": post})

async def post_edit_post(request: StarletteRequest):
    if not request.user.is_authenticated:
        return RedirectResponse(url="/login", status_code=303)
    post_id = request.path_params["id"]
    post = db_session.get_post_by_id(post_id)
    if not post or post.author_id != request.user.id:
        return PlainTextResponse("Unauthorized or Post not found", status_code=404)
        
    form = await request.form()
    title = form.get("title", "").strip()
    category = form.get("category", "").strip()
    summary = form.get("summary", "").strip()
    content = form.get("content", "").strip()
    status = form.get("status", "draft").strip()
    media_url = post.media_url

    media_upload = form.get("media")
    remove_media = form.get("remove_media") == "1"
    if media_upload and getattr(media_upload, "filename", None):
        content_type = (getattr(media_upload, "content_type", "") or "").split(";", 1)[0].lower()
        if not is_allowed_media_type(content_type):
            return app_templates.TemplateResponse(
                request, "post_edit.html",
                {"action": "edit", "post": post, "error": "Only image, video, audio, and PDF files are supported."}
            )
        file_bytes = await media_upload.read()
        saved_path = save_uploaded_file(file_bytes, media_upload.filename)
        if saved_path:
            media_url = build_media_url(saved_path)
    elif remove_media:
        media_url = None
    
    if not title or not content:
        return app_templates.TemplateResponse(
            request, "post_edit.html", 
            {"action": "edit", "post": post, "error": "Title and Content are required."}
        )
        
    if title != post.title:
        slug = slugify(title)
        base_slug = slug
        counter = 1
        while True:
            existing = db_session.get_post_by_slug(slug)
            if existing is None or existing.id == int(post_id):
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
    else:
        slug = post.slug
        
    if remove_media and post.media_url:
        delete_uploaded_file(post.media_url)

    success = db_session.update_post(int(post_id), title, slug, category, summary, content, status, request.user.id, media_url)
    if not success:
        return app_templates.TemplateResponse(
            request, "post_edit.html", 
            {"action": "edit", "post": post, "error": "Failed to update post."}
        )
    else:
        username: str = get_current_username(request)
        await update_data_in_chroma(username, str(content), str(slug), str(category), str(title), str(summary))       
        return RedirectResponse(url="/dashboard", status_code=303)

async def post_delete(request: StarletteRequest):
    if not request.user.is_authenticated:
        return RedirectResponse(url="/login", status_code=303)
    post_id = request.path_params["id"]
    db_session.delete_post(int(post_id), request.user.id)
    return RedirectResponse(url="/dashboard", status_code=303)

async def media_upload(request: StarletteRequest):
    if not request.user.is_authenticated:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    form = await request.form()
    media_upload = form.get("file")
    if not media_upload or not getattr(media_upload, "filename", None):
        return JSONResponse({"error": "No file provided"}, status_code=400)

    content_type = (getattr(media_upload, "content_type", "") or "").split(";", 1)[0].lower()
    if not is_allowed_media_type(content_type):
        return JSONResponse({"error": "Only image, video, audio, and PDF files are supported"}, status_code=400)

    file_bytes = await media_upload.read()
    saved_path = save_uploaded_file(file_bytes, media_upload.filename)
    if not saved_path:
        return JSONResponse({"error": "Unable to save file"}, status_code=500)

    return JSONResponse({"url": build_media_url(saved_path), "name": media_upload.filename})

async def query_data(request: StarletteRequest):
    
    try:
        data = await request.json()
        print('received query json: ',  data)
        
        querytext = data.get("querytext", "").strip()
        
        searchinpostsstr = str(data.get("searchinposts", "")).strip()
        searchinposts = False
        try:
            if searchinpostsstr.isdigit():
                searchinpostsint = int(searchinpostsstr)
                if searchinpostsint > 0:
                    searchinposts = True
        except Exception as e:
            searchinposts = False

        lookupnumstr = data.get("lookupnum", "").strip()
        lookupnum = 0
        try:
            if lookupnumstr.isdigit():
                lookupnum = int(lookupnumstr)
        except Exception as e:
            lookupnum = 0
            
        username: str = get_current_username(request)
        print('received query',  f'user={username} querytext={querytext} searchinposts={searchinposts} lookupnum={lookupnum}')

        result = await agent_manager.call_agent_async(username, querytext, searchinposts, lookupnum)
        
        #print('received query agent result: ', result)
        

        if result is None:
            return JSONResponse({"status": "error", "message": "Agent returned no response."}, status_code=400)
        else:
            if isinstance(result, tuple) and len(result) == 2:
                status_code, response_text = result
                if status_code != 1:
                    return JSONResponse({"status": "error", "message": response_text}, status_code=400)
            else:
                return JSONResponse({"status": "error", "message": "Unexpected agent response format."}, status_code=400)
        
            response_text = re.sub(r'\r\n|\r|\n', ' ', response_text)
            return JSONResponse({"status": "success", "message": response_text}, status_code=200)
        
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

async def add_data_to_chroma(username:str, content: str, slug: str, category: str, title: str, summary: str):
    
    if content is None:
        return -11
    
    if app_chromaconnector is None:
        return -12

    content_text = app_chromaconnector.HtmlToText(str(content))
    
    if len(content_text) < 1:
        return -13
    
    return await app_chromaconnector.add_data(username, slug, content_text, {"category": category, "title": title, "summary": summary})

async def update_data_in_chroma(username:str, content: str, slug: str, category: str, title: str, summary: str):
    
    #print('was called update_data_in_chroma')
    
    if content is None:
        return -11
    
    if app_chromaconnector is None:
        return -12

    content_text = app_chromaconnector.HtmlToText(str(content))
    
    if len(content_text) < 1:
        return -13
    
    return await app_chromaconnector.update_data(username, slug, content_text, {"category": category, "title": title, "summary": summary})

        
app_routes = [
    Route("/", endpoint=home, methods=["GET"]),
    Route("/login", endpoint=login_get, methods=["GET"]),
    Route("/login", endpoint=login_post, methods=["POST"]),
    Route("/register", endpoint=register_get, methods=["GET"]),
    Route("/register", endpoint=register_post, methods=["POST"]),
    Route("/dashboard", endpoint=dashboard, methods=["GET"]),
    Route("/logout", endpoint=logout, methods=["GET"]),
    Route("/post/{slug}", endpoint=post_detail, methods=["GET"]),
    Route("/dashboard/new", endpoint=post_new_get, methods=["GET"]),
    Route("/dashboard/new", endpoint=post_new_post, methods=["POST"]),
    Route("/dashboard/edit/{id:int}", endpoint=post_edit_get, methods=["GET"]),
    Route("/dashboard/edit/{id:int}", endpoint=post_edit_post, methods=["POST"]),
    Route("/dashboard/delete/{id:int}", endpoint=post_delete, methods=["GET", "POST"]),
    Route("/dashboard/media/upload", endpoint=media_upload, methods=["POST"]),
    Route("/api/query", endpoint=query_data, methods=["POST"]),
    Mount("/static", app=StaticFiles(directory="advcms/static"), name="static"),
]