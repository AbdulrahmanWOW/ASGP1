# أسئلة وأجوبة مناقشة مشروع ASGP

هذا الملف يجمع الأسئلة التي بدأت من طلب "اعتبرني أنا الدكتور" والأسئلة التابعة لها، بصياغة مناسبة للمراجعة قبل المناقشة.

## السؤال 1: اشرح المشروع من البداية كأنك تعرضه على الدكتور

ASGP منصة Security Governance للأدوات التي تستخدمها AI Agents. تسجل نية المستخدم وصلاحياته في Intent Anchor، ثم تفحص كل Tool Call قبل التنفيذ من خلال Request integrity وPolicies وIntent alignment وPrompt-injection وBehavior وRisk. القرار النهائي يكون `ALLOW` أو `BLOCK` أو `ESCALATE`. كل قرار يسجل بعد إخفاء الأسرار في Tamper-evident audit ويظهر على Dashboard.

المثال الأساسي: المستخدم يطلب قراءة رسائل Demo وعمل Summary محلي. القراءة مسموحة. إذا احتوت رسالة على تعليمات تطلب إرسال بيانات للخارج وحاول الـAgent تنفيذ `send_email`، يمنع ASGP التنفيذ لأن الأداة أو الوجهة خارج نية المستخدم وصلاحياته.

المساهمة ليست ادعاء اختراع Detector مثالي، وإنما تنفيذ Security middleware كامل يجمع pre-execution enforcement وhuman approval وreplay defense وexplainable risk وaudit وتقييم قابل للتكرار.

## السؤال 2: هل المشروع انتهى وجاهز للعرض؟

المشروع مكتمل كـGraduation Security Prototype، وتعمل مكوناته الأساسية واختباراته وDashboard والتقييم. يمكن عرضه على لجنة. للحصول على Demo أكثر إقناعًا يفضل إضافة Agent Simulator يبدأ من User Task ويستخدم الـSDK أمام اللجنة، لأن Evaluation runner الحالي يتعامل مع الـGateway مباشرة. لا يحتاج ذلك إلى ChatGPT أو LLM مدفوع؛ Agent محلي deterministic كافٍ لإثبات Integration.

## السؤال 3: هل يجب ربطه بـAgent معين؟

لا. التصميم الصحيح أن يكون Model-agnostic وFramework-agnostic لكنه Integration-dependent. أي Agent يمكنه استخدام النظام إذا مرر Tool Calls عبر REST API أو SDK أو Adapter أو MCP Proxy. الأدوات التي تتجاوز هذه الحدود ليست تحت حماية ASGP.

## السؤال 4: كيف يعمل الـDetection؟ وهل يوجد AI؟

الـDetection هجين وليس AI فقط:

```text
Hard deterministic checks
→ Intent alignment
→ Injection detection
→ Behavioral analysis
→ Risk aggregation
→ Decision
```

القواعد الصريحة تفحص Session وTool permissions والمسارات والوجهات والتوقيع والـReplay. لا تحتاج هذه الأشياء إلى AI، ولها الأولوية.

جزء Intent alignment مصمم من خلال `AIProvider` يعيد `score`, `reason`, و`risk_factors`. النسخة الحالية تستخدم MockProvider deterministic حتى تعمل الاختبارات بلا API key أو تكلفة وتبقى النتائج قابلة للتكرار. يمكن لاحقًا إضافة OpenAI أو Anthropic أو Gemini أو Local Provider دون تغيير بقية الـPipeline.

Prompt-injection detection الحالي يعتمد على explainable patterns مثل instruction override وطلب إرسال secrets وإخفاء الفعل. Behavioral analysis يتابع تسلسل الأفعال مثل عدة Reads ثم Upload خارجي. كل Layer تنتج Finding وRisk delta؛ الـAI لا يعيد قرار `ALLOW` مباشرًا.

إذا فشل AI Provider أو أعاد Schema غير صحيح، يتحول الفشل إلى `AI_PROVIDER_FAILURE` ومخاطر إضافية بدل افتراض أن الطلب آمن.

## السؤال 5: لماذا لا نترك الـAgent يقرر أن الطلب خبيث؟

الـAgent نفسه جزء من سطح الهجوم. الـLLM احتمالي ويمكن أن يتأثر بمحتوى خارجي أو ينسى القيود خلال سلسلة طويلة. لذلك يجب أن يكون قرار التفويض في طبقة مستقلة deterministic، وأن يكون AI signal عاملًا مساعدًا لا سلطة نهائية.

## السؤال 6: هل Regex كافية لاكتشاف Prompt Injection؟

لا. هي سريعة ومفسرة لكنها قد تفشل مع إعادة الصياغة أو الترميز أو اللغات المختلفة، وقد تعتبر اقتباسًا بريئًا هجومًا. هذا ظهر كـFalse Positive في التقييم. التطوير الطبيعي هو Fast heuristic أولًا، ثم Context-aware model للحالات غير الواضحة، مع بقاء Hard policies صاحبة القرار الأعلى.

## السؤال 7: ما الـLayers الموجودة حاليًا؟

الموجود فعليًا:

1. Session validation.
2. Intent Anchor وversioned permissions.
3. Tool registry.
4. Ed25519 request integrity وreplay defense.
5. Deterministic policy engine.
6. Intent alignment provider interface وMockProvider.
7. Prompt-injection heuristics.
8. Stateful behavioral rules.
9. Explainable risk engine.
10. Decision precedence لـAllow/Block/Escalate.
11. Human approval وsession revocation.
12. Redaction وtamper-evident audit.
13. Metrics وper-stage latency.
14. Dashboard وAttack Lab وevaluation.

## السؤال 8: ما الـLayers التي لم ننفذها أو بسطناها؟

- Redis: لم نحتجه في single-machine MVP.
- WebSockets: استبدلت بـPolling.
- Real AI provider: يوجد Contract وMock فقط.
- Advanced ML injection classifier: استبدل بـheuristics.
- Automatic content-ingress gateway: يوجد scanner لكن ليس Proxy كاملًا لكل Email/PDF/RAG result.
- ML behavioral IDS: استبدل بقواعد stateful مفسرة.
- Separate trust engine: دمج في Risk score واحدة.
- Generic process `TERMINATE`: استبدل بـSession revocation.
- Signed multi-agent delegation chain: غير منفذ.
- Arbitrary code sandbox: خارج النطاق.
- Enterprise KMS وSSO وRBAC وmulti-tenancy: خارج MVP.
- External immutable audit anchoring: الموجود hash chain داخل قاعدة البيانات.
- Large 100–200 scenario dataset: الموجود 12 سيناريو.
- Fully orchestrated live demo agent: أهم تحسين تالٍ.

## السؤال 9: لماذا دمجنا Trust وRisk؟

وجود رقمين مستقلين قد يخلق تناقضًا وغموضًا. استخدمنا Risk score واحدة من 0 إلى 100، وكل تغيير فيها له Previous وDelta وNew وReason. هذا أسهل في التفسير والاختبار أمام اللجنة.

## السؤال 10: لماذا `TERMINATE` أصبحت Session Revocation؟

ASGP لا يملك بالضرورة Process الـAgent أو Container الذي يعمل فيه. لذلك ادعاء Kill عام غير واقعي. ما يستطيع النظام ضمانه داخل حدوده هو إلغاء Session ورفض كل Tool Calls اللاحقة.

## السؤال 11: هل الـAudit غير قابلة للتعديل؟

الوصف الصحيح هو Tamper-evident وليس Tamper-proof. Hash chaining يسمح باكتشاف تغيرات في السلسلة، لكنه لا يمنع شخصًا يملك قاعدة البيانات من حذفها بالكامل ولا يوفر External trusted timestamp. الإنتاج يحتاج append-only storage أو external anchoring.

## السؤال 12: ما نتائج التقييم وكيف نفسرها؟

على Dataset صغيرة ومحكومة: malicious detection يساوي 100%، ambiguous escalation يساوي 100%، exact accuracy تساوي 91.7% وfalse-positive rate بين الحالات الشرعية تساوي 25%. Policy-only انخفض بها malicious detection إلى 66.7%. هذا يوضح أن الإشارات الدلالية التقطت هجمات فاتت السياسات، لكنها أضافت False Positive في اقتباس شرعي للغة هجوم.

لا يجوز تعميم النسب على العالم الحقيقي بسبب صغر Dataset وطبيعتها المصممة للمختبر.

## السؤال 13: من المنافسون وما الفرق؟

الفئة تشمل Prompt Shields وCloud guardrails وأطرًا مثل NeMo Guardrails وLlamaFirewall. كثير منها أوسع أو أقوى إنتاجيًا. تركيز ASGP هو Tool-action governance: Intent وصلاحيات وSignatures وpre-execution decision وhuman approval وsession risk وhash-chained audit في Prototype واحد قابل للدراسة. المقارنة العلمية هي اختلاف نطاق وتركيز، وليست ادعاء تفوق عام.

## السؤال 14: كيف نحول النظام إلى Product متصل بأي Agent؟

نحافظ على Core API واحدة ونقدم عدة Integration options:

1. Generic REST API لأي لغة.
2. Python SDK الموجود وتطوير JavaScript SDK.
3. Adapters لـLangChain وOpenAI Agents وCrewAI وAutoGen.
4. MCP Security Proxy يمرر Tool Calls المسموحة إلى MCP servers الحقيقية.
5. Central Tool Execution Gateway يحتفظ بالـCredentials وينفذ الأدوات بدل الـAgent.

الشكل الأقوى:

```text
Agent
  ↓
SDK / Framework Adapter / MCP Proxy
  ↓
ASGP Enforcement Gateway
  ↓
Policy + Detection + Approval + Audit
  ↓
ASGP-managed Tool Connector
  ↓
Real service
```

## السؤال 15: كيف نمنع Agent من تجاوز الـSDK؟

الـSDK-only integration يمكن تجاوزه إذا امتلك الـAgent الأداة الأصلية أو Credentials. المنتج الحقيقي يجب أن يعزل Credentials عن الـAgent ويجعل Network path أو Tool endpoint متاحًا فقط عبر ASGP. Central execution gateway أو MCP proxy/sidecar أقوى من Wrapper اختياري.

## السؤال 16: ما خطة Productization الواقعية؟

### الخطوة الأولى

Demo Agent متكامل، Reset/Seed command، وثلاثة مسارات Allow/Block/Escalate.

### الخطوة الثانية

REST contract عام، Python/JS SDKs، MCP Proxy، framework adapters، API authentication وidempotency.

### الخطوة الثالثة

Credential isolation، tool connectors، multi-tenancy، RBAC، SSO،secret manager،rate limiting وaudit export.

### الخطوة الرابعة

Real/local AI providers، multilingual classifier، context-aware detection، Dataset أكبر وthreshold calibration.

## السؤال 17: ما الجملة الختامية المناسبة أمام اللجنة؟

> ASGP لا يدعي جعل أي AI Agent آمنًا بصورة مطلقة، لكنه يقدم طبقة مستقلة ومفسرة وقابلة للاختبار تمنع الأدوات المتكاملة من تنفيذ أفعال خارج نية المستخدم وصلاحياته قبل وقوع الضرر.
