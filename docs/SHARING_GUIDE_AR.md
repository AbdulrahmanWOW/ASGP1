# دليل مشاركة مشروع ASGP — اختر طريقة واحدة فقط

## الإجابة المختصرة

**لا، لست مطالبًا بتنفيذ كل الطرق. اختر طريقة واحدة حسب هدفك:**

| هدفك | الطريقة المناسبة | التقييم |
|---|---|---|
| مشاركة المشروع مع الفريق ليستمروا في تطويره | GitHub | الأفضل والمُوصى بها |
| إرسال نسخة سريعة للدكتور أو صديق | ZIP نظيف | الأسهل، لكن غير مناسب للتعاون المستمر |
| تشغيل النظام دون مشاركة Source Code | Docker Images | مناسب للعرض/التسليم، لكنه أعقد |

في جميع الحالات، Docker هو **طريقة تشغيل** وليس بالضرورة طريقة مشاركة. مثلًا يمكنك مشاركة الكود عبر GitHub، ثم يستخدم صديقك Docker لتشغيله.

# الطريقة الأولى: GitHub — الأفضل للفريق

## استخدمها عندما

- تريد مشاركة المشروع مع زملائك.
- كل شخص سيعدل جزءًا مختلفًا.
- تريد الاحتفاظ بتاريخ التعديلات.
- تريد مراجعة التغييرات واسترجاع نسخة قديمة.

## ما يحتاجه صاحب المشروع مرة واحدة

1. أنشئ Repository فارغة على GitHub، مثل `asgp`.
2. افتح PowerShell داخل `D:\Grad`.
3. نفذ:

```powershell
git init
git add .
git status
git commit -m "Complete ASGP graduation project"
git branch -M main
git remote add origin https://github.com/USERNAME/asgp.git
git push -u origin main
```

استبدل `USERNAME` باسم حسابك. افحص `git status` قبل الـCommit وتأكد أن `.env` وAPI keys وPrivate keys وقواعد البيانات غير موجودة.

## ماذا يفعل صديقك؟

```powershell
git clone https://github.com/USERNAME/asgp.git
cd asgp
docker-compose up --build
```

ثم يفتح:

- Dashboard: `http://127.0.0.1:4173`
- API documentation: `http://127.0.0.1:8000/docs`

## المميزات

- أفضل اختيار للتعاون.
- كل الملفات والإصدارات في مكان واحد.
- Branches لكل عضو وPull Requests للمراجعة.
- تنزيل التعديلات الجديدة عبر `git pull` بدل إرسال المشروع كاملًا من جديد.
- يمكن جعل Repository خاصة وإضافة أعضاء الفريق فقط.

## العيوب

- يحتاج تعلم أساسيات Git.
- Conflict ممكن إذا عدل شخصان نفس الأسطر.
- يجب الانتباه جدًا لعدم رفع Secrets.
- أول Docker build يحتاج إنترنت ووقتًا.

## الحكم

**هذه هي الطريقة التي أنصحكم باستخدامها للمشروع.** شاركوا Source Code عبر Private GitHub Repository وشغلوه باستخدام Docker Compose.

# الطريقة الثانية: ZIP نظيف — الأسهل للإرسال مرة واحدة

## استخدمها عندما

- تريد إرسال Snapshot ثابتة للدكتور.
- صديقك يريد مشاهدة المشروع فقط.
- لا تريد إعداد GitHub الآن.
- سترسل النسخة عبر Drive أو USB أو خدمة ملفات.

## أفضل طريقة لإنشاء ZIP إذا كنت تستخدم Git

بعد وجود Commit ناجح:

```powershell
git archive --format=zip --output=ASGP-project.zip HEAD
```

الملف الناتج يحتوي على الملفات المتتبعة فقط، ولا يضم `.venv` أو `node_modules` أو `.env` إذا كانت إعدادات Git صحيحة.

## إذا لم تكن تستخدم Git

1. أنشئ نسخة جديدة من مجلد المشروع.
2. احذف من **النسخة فقط**:

```text
.venv/
node_modules/
frontend/dist/
__pycache__/
.pytest_cache/
.ruff_cache/
.env
*.db
```

3. تأكد من عدم وجود API keys أوPrivate keys.
4. اضغط النسخة إلى `ASGP-project.zip`.
5. أرسل معها رابط هذا الدليل.

## كيف يشغل صديقك نسخة ZIP؟

بعد فك الضغط:

```powershell
cd ASGP-project
docker-compose up --build
```

ثم يفتح `http://127.0.0.1:4173`.

## المميزات

- بسيط جدًا.
- مناسب للتسليم النهائي أو النقل على USB.
- لا يحتاج حساب GitHub.

## العيوب

- لا يوجد تاريخ تعديلات.
- كل تحديث يتطلب إرسال ZIP جديدة.
- قد يحدث لخبطة في أسماء مثل `final`, `final2`, `final-last`.
- دمج تعديلات أعضاء الفريق صعب.
- ضغط مجلد العمل دون تنظيف قد يضم Secrets أو ملفات بحجم ضخم.

## الحكم

جيد للدكتور أو Snapshot نهائية، لكنه **ليس الاختيار الأفضل لعمل الفريق اليومي**.

# الطريقة الثالثة: Docker Images — تشغيل بدون Source Code

## استخدمها عندما

- تريد إعطاء جهة ما نسخة قابلة للتشغيل دون الكود.
- تريد تثبيت نفس Backend وFrontend versions.
- لديك Docker Registry مثل Docker Hub أو GitHub Container Registry.

## الفكرة

أنت تبني Images ثم ترفعها إلى Registry:

```text
username/asgp-backend:1.0
username/asgp-frontend:1.0
```

ويستخدم صديقك Compose file تشير إلى هذه Images بدل `build:`.

مثال البناء والرفع:

```powershell
docker build -t USERNAME/asgp-backend:1.0 ./backend
docker build -t USERNAME/asgp-frontend:1.0 ./frontend
docker login
docker push USERNAME/asgp-backend:1.0
docker push USERNAME/asgp-frontend:1.0
```

بعدها يحتاج صديقك إلى Compose file وقيم الإعدادات، ثم:

```powershell
docker-compose pull
docker-compose up
```

## المميزات

- نفس بيئة التشغيل تقريبًا على كل جهاز.
- لا يحتاج المستلم تثبيت Python أو Node packages.
- يمكنك مشاركة نسخة تشغيل دون Source Code.
- مناسب للإصدارات والعروض المنظمة.

## العيوب

- أعقد من GitHub وZIP.
- يحتاج Registry وحسابًا وإدارة Tags.
- الـImages قد تكون كبيرة.
- لا يفيد زملاءك إذا كانوا سيعدلون الكود.
- PostgreSQL data ليست جزءًا من Image وتظل Volume منفصلة.
- يجب إدارة Environment variables وSecrets بصورة منفصلة.

## الحكم

مفيد لاحقًا كـProduct delivery، لكن **ليس أول اختيار لفريق مشروع تخرج يريد تطوير الكود معًا**.

# طريقة رابعة اختيارية: USB أو Google Drive

هذه ليست طريقة تقنية مختلفة؛ هي مجرد وسيلة لنقل ملف ZIP النظيف. اتبع خطوات ZIP السابقة، ثم ارفع الملف إلى Drive أو انقله على USB.

المميزات: سهلة ولا تحتاج Git knowledge. العيوب: نفس عيوب ZIP، ولا توفر Version Control أو تعاونًا حقيقيًا.

# تشغيل المشروع بدون Docker

هذا بديل تشغيل فقط، ويمكن استخدامه سواء حملت المشروع من GitHub أو ZIP:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:ASGP_DATABASE_URL = "sqlite+pysqlite:///./asgp.db"
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

وفي Terminal أخرى من جذر المشروع:

```powershell
cd frontend
pnpm install
pnpm dev
```

هذه الطريقة مفيدة للمطور، لكنها تحتاج Python وNode.js وpnpm وإعدادًا أكثر من Docker.

# اقتراحي النهائي لكم

نفذوا **هذه الخطة فقط**:

1. أنشئ Private GitHub Repository.
2. ارفع Source Code بعد التأكد من عدم وجود Secrets.
3. أضف أصحابك كـCollaborators.
4. كل عضو يعمل على Branch منفصلة.
5. شغلوا المشروع باستخدام `docker-compose up --build`.
6. وقت التسليم، أنشئ GitHub Release أو ZIP باستخدام `git archive`.

هذا يجمع أفضل طريقة للتعاون مع أسهل طريقة لتوحيد التشغيل.

# Checklist قبل أي مشاركة

- `.env` غير موجودة في الملفات المرفوعة.
- لا توجد API keys أوPrivate keys.
- لا تشارك `.venv` أو`node_modules`.
- `docker-compose config` ينجح.
- Backend tests وFrontend build ينجحان.
- شارك `evaluation/latest/REPORT.md` وملفات `docs/`.
- أخبر الفريق أن ASGP يحمي الأدوات المارة عبر SDK/Gateway فقط.
