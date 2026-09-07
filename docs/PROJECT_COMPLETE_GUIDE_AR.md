# الدليل الكامل لمشروع ASGP

## 1. تعريف المشروع

**ASGP — Agent Security Governance Platform** منصة أمنية تعمل بين وكيل الذكاء الاصطناعي والأدوات التي يستطيع استخدامها. لا تسمح المنصة بتنفيذ Tool Call حساس قبل فحصه، ثم تعيد أحد القرارات التالية:

- `ALLOW`: السماح بالتنفيذ.
- `BLOCK`: منع التنفيذ قبل حدوثه.
- `ESCALATE`: إيقاف التنفيذ مؤقتًا وانتظار قرار بشري.

المشروع لا يدعي حماية أي Agent بصورة مطلقة؛ نطاق الحماية هو الأدوات التي تم تسجيلها وتمريرها عبر ASGP SDK أو الـGateway.

## 2. المشكلة

أصبح الـAI Agent قادرًا على قراءة الملفات والرسائل، الاتصال بخدمات خارجية، إرسال بريد، رفع بيانات وتشغيل أدوات. قد يبدأ المستخدم بطلب شرعي مثل: "اقرأ رسائل الـDemo واكتب ملخصًا محليًا"، لكن رسالة خبيثة قد تحتوي على تعليمات غير موثوقة تطلب من الـAgent إرسال أسرار إلى الخارج. الاعتماد على الـLLM وحده غير كافٍ لأنه احتمالي ويمكن أن يسيء تفسير الصلاحيات.

ASGP ينقل قرار الأمان إلى طبقة مستقلة تعمل قبل التنفيذ.

## 3. المسار الكامل

```text
User Intent
    ↓
Intent Anchor + Permissions
    ↓
Integrated AI Agent
    ↓
ASGP SDK / Tool Wrapper
    ↓
Signed Action Request
    ↓
Session → Integrity → Policy → Alignment → Injection → Behavior → Risk
    ↓
ALLOW / BLOCK / ESCALATE
    ↓
Tool Execution أو Human Approval
    ↓
Tamper-Evident Audit + Dashboard
```

## 4. ما تم إنجازه عبر مراحل المشروع

### Phase 0 — Foundation

- هيكل Backend وSDK وDemo وDocumentation.
- FastAPI وPydantic contracts.
- تعريف قرارات `ALLOW/BLOCK/ESCALATE`.
- Threat model وMVP scope وArchitecture decisions.
- Safe logging وconfiguration.

### Phase 1 — أول مسار أمني متكامل

- إنشاء Session بغاية وصلاحيات.
- Tool registry.
- Python tool wrapper.
- السماح والمنع قبل التنفيذ.
- Fail-closed عند فشل الاتصال.
- Counted demo tools تثبت أن الأداة المحجوبة لم تعمل.
- Audit event قابل للتفسير.

### Phase 2 — التخزين والسياسات

- PostgreSQL وSQLAlchemy وAlembic migrations.
- تخزين Sessions وIntent anchors وPolicies وActions وDecisions وAudit.
- Versioned Intent Anchor.
- Structured JSON policies دون `eval` أو تنفيذ نصوص.
- حدود الملفات والوجهات الخارجية.
- Redaction للحقول الحساسة.

### Phase 3 — Risk وHuman Approval

- Risk score من 0 إلى 100.
- تسجيل القيمة السابقة والتغيير والقيمة الجديدة والسبب.
- Expiring approvals.
- ربط الموافقة بـAction Digest محدد.
- منع إعادة استخدام Approval لطلب آخر أو Parameters معدلة.
- Session revocation كبديل واقعي عن قتل Process لا يملكه النظام.

### Phase 4 — سلامة الطلب ومنع Replay

- Canonical serialization.
- SHA-256 action digests.
- Ed25519 agent signatures.
- Agent registration وrevocation.
- Nonce وtimestamp وexpiry وmonotonic sequence.
- منع الطلبات المعدلة أو المكررة أو المنتهية أو الموقعة خطأ.

### Phase 5 — الإشارات الدلالية والسلوكية

- `AIProvider` abstraction غير مرتبط بمزود واحد.
- `MockProvider` محلي deterministic للاختبارات.
- Intent alignment score وrisk factors.
- Prompt-injection heuristics مع confidence وevidence.
- اكتشاف repeated denials وdata staging وreconnaissance.
- دمج كل Finding في Risk Engine.

### Phase 6 — Audit وObservability

- SHA-256 hash chain لكل Session.
- `previous_hash` و`entry_hash` وsequence.
- اكتشاف تعديل أو حذف Event عندما تسمح استمرارية السلسلة.
- Per-stage timings وtotal latency.
- Pipeline metrics.
- اختبارات تمنع ظهور secrets في Events أو Logs.

### Phase 7 — Dashboard

- React + TypeScript + Vite dashboard.
- Command Center وحالة الاتصال.
- Sessions وIntent وpermission boundaries.
- Risk history وdecision stream.
- Human approvals مع Approve وReject.
- Audit verification ظاهر للمستخدم.
- Event drawer بشرح بسيط وتقني وFindings وTimings.
- Polling كل خمس ثوانٍ.
- CORS محصور على بيئة التشغيل المحلية.
- Dockerfiles وDocker Compose.

### Phase 8 — Attack Lab والتقييم والتسليم

- Controlled local inbox وfile area وmail sender وupload sink.
- منع الخروج من مجلد الـLab أو الاتصال بوجهات حقيقية.
- 12 سيناريو معلّم: 4 legitimate و2 ambiguous و6 malicious.
- Evaluation runner قابل للتكرار.
- Full-pipeline وpolicy-only ablation.
- JSON وCSV وMarkdown reports.
- Deployment guide وDemo script وLimitations وPresentation outline ورسومات للرسالة.

## 5. طبقات الحماية الحالية

### Session Validation

تتحقق من وجود Session وأنها Active وتستعمل أحدث نسخة من Intent Anchor. الـSession الملغاة لا تستطيع إرسال أفعال جديدة.

### Tool Registry

كل Tool لها اسم ووصف وSensitivity وإمكانية اشتراط Signature. أي Tool غير مسجلة تفشل Fail-closed.

### Cryptographic Verification

Ed25519 والتوقيع والـnonce والـtimestamp والـexpiry والـsequence تثبت أصل الطلب وسلامته وتمنع Replay. التوقيع الصحيح لا يعني أن الفعل آمن.

### Deterministic Policy Engine

يفحص allowlist وdenylist ومسارات الملفات والوجهات الخارجية والسياسات المنظمة. المخالفة الصريحة لا يستطيع AI score تجاوزها.

### Intent Alignment

يقارن نية المستخدم بالأداة المطلوبة ويعيد نتيجة منظمة. التنفيذ الحالي يستخدم MockProvider محليًا لضمان نتائج مجانية وقابلة للتكرار.

### Prompt-Injection Detector

يكتشف instruction override وauthority impersonation وطلبات exfiltration والأفعال المخفية وبعض الـencoded payloads. النسخة الحالية heuristic وليست ضمانًا كاملاً.

### Behavioral Analyzer

يتابع تاريخ الجلسة ويكتشف أنماطًا مثل عدة عمليات قراءة تليها محاولة إرسال خارجي أو تكرار المحاولات المحجوبة.

### Risk and Decision Engine

يجمع Tool sensitivity والإشارات الدلالية والسلوكية في Risk score واضحة. المخاطر المنخفضة تسمح، والمتوسطة تصعّد للبشر، والمرتفعة تمنع. Hard violations تمنع مباشرة.

### Active Response

الأداة لا تنفذ قبل `ALLOW` أو Approval صحيح. يمكن رفض الطلب أو إلغاء الـSession. النظام لا يدعي قتل Agent process أو Container.

### Audit and Observability

كل قرار يسجل بعد Redaction مع أسبابه ومخاطره وتوقيته وHash chain يمكن التحقق منها.

## 6. نموذج البيانات الأساسي

- `Session`: سياق الأمان وحالة الجلسة.
- `IntentAnchor`: نية المستخدم والصلاحيات والنسخة والـHash.
- `AgentIdentity`: هوية Agent ومفتاحه العام وحالته.
- `ToolDefinition`: تعريف Tool وحساسيتها.
- `Policy`: قاعدة منظمة وآمنة.
- `ActionRequest`: الطلب الكامل قبل التنفيذ.
- `SecurityFinding`: إشارة أمنية مع Evidence وConfidence.
- `RiskChange`: انتقال مفسر في درجة المخاطر.
- `Decision`: القرار وأسبابه وTiming.
- `Approval`: موافقة بشرية مرتبطة بفعل واحد.
- `AuditEvent`: سجل منقح ومربوط بالـHash السابق.

## 7. حماية الأسرار

حقول مثل `password`, `secret`, `token`, `api_key` و`authorization` يتم تنقيحها قبل التخزين، فتظهر كـ`[REDACTED]` في السجل والواجهة والتقارير.

## 8. نتائج التقييم الحالية

النتائج تخص الـControlled dataset فقط ولا تعني أداءً عامًا في العالم الحقيقي:

| المقياس | النتيجة |
|---|---:|
| عدد السيناريوهات | 12 |
| Exact decision accuracy | 91.7% |
| Malicious detection rate | 100% |
| Ambiguous escalation rate | 100% |
| Legitimate false-positive rate | 25% |
| Median pipeline latency | نحو 10.8 ms على جهاز الاختبار |
| P95 pipeline latency | نحو 13.3 ms على جهاز الاختبار |

تم الاحتفاظ بحالة False Positive تقتبس لغة هجوم داخل تقرير شرعي. الـFull pipeline منعها، بينما policy-only لم يكتشف هجومين دلاليين. هذا يوضح Trade-off حقيقيًا بين Detection وFalse Positives.

## 9. ما تم تبسيطه أو لم ينفذ

| الـVision | التنفيذ الحالي |
|---|---|
| Universal protection | حماية الأدوات المارة عبر SDK/Gateway فقط |
| Real AI classifier | MockProvider وheuristics قابلة للاستبدال |
| ML behavioral IDS | Explainable stateful rules |
| Trust وRisk منفصلان | Risk score واحدة واضحة |
| `TERMINATE` عام | Session revocation |
| Tamper-proof storage | Tamper-evident hash chain |
| Multi-agent delegation chain | Agent identity واحدة حاليًا |
| Redis وdistributed deployment | PostgreSQL وsingle-machine Docker Compose |
| WebSocket | Polling كل خمس ثوانٍ |
| 100–200 سيناريو | 12 سيناريو لإثبات منهج التقييم |
| Arbitrary-code sandbox | خارج نطاق المشروع |
| Enterprise KMS/RBAC/SSO | خارج MVP |

## 10. المنافسة والتميّز

هناك حلول لحماية Prompts ومخرجات النماذج وأطر Guardrails واسعة. تميّز ASGP كـGraduation Prototype هو جمع Intent anchoring وpre-execution tool enforcement وpolicy وsignatures وbehavior وhuman approval وaudit والتقييم في مسار واحد مفسر. لا ندعي التفوق الإنتاجي على منتجات الشركات الكبرى، بل نقدم Architecture كاملة قابلة للفحص والتطوير.

## 11. القيمة المقترحة

> اربط أدوات الـAI Agent عبر ASGP، وطبّق نية المستخدم والسياسات والمخاطر والموافقة البشرية والتدقيق قبل كل فعل حساس.

## 12. حالة المشروع

- الـCore architecture مكتملة.
- Backend وSDK وDashboard وAttack Lab تعمل.
- 57 اختبار automated tests ناجحة وقت التسليم.
- Frontend production build وlint ناجحان.
- المشروع جاهز كمشروع تخرج قوي.
- أهم تطوير إضافي للعرض أو المنتج هو Demo Agent متكامل ثم MCP/Framework adapters وcentral tool execution لمنع الـBypass.
