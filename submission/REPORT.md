# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Chu Thuỳ Dương
- **MSSV:** 2A202602660
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/VinUni-AI20k/K4-L3-DAY13-ChuThuyDuong-2A202602660-Monitoring-LLMOps
- **Commit SHA cuối:** HEAD
- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** day13-k4-l3b-02660

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 0/100 | 100/100 | Đạt toàn bộ 4 tiêu chuẩn: JSON schema, Correlation ID, Log enrichment, PII scrubbing |
| `validate_dashboard.py` | 0/6 panel | 6/6 panel | Hợp lệ toàn bộ 6 panel theo contract YAML |
| `pytest` | 22 passed | 25 passed | Vượt qua 100% test cases, đã viết thêm test cho CCCD, thẻ ngân hàng, passport |
| Số traces hợp lệ | 0 | 25+ traces | Đầy đủ cấu trúc cây 3 cấp (Agent -> Retrieval + Generation) trên Langfuse |
| Số PII leak | Chưa kiểm soát | 0 | Đã lọc sạch email, số điện thoại VN, CCCD, thẻ tín dụng |
| Latency P95 / TTFT P95 | 846.5ms / 50.0ms | 3,154.7ms / 50.0ms | TTFT ổn định, phát hiện độ trễ tăng cao do bước retrieval bị nghẽn |
| Retrieval success rate | 100% | 100% | Retrieval vẫn trả về tài liệu thành công, không bị crash |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong file app/middleware.py, mỗi request đi vào trước tiên được xoá context cũ bằng hàm clear_contextvars(). Sau đó middleware kiểm tra header x-request-id; nếu client đã gửi thì dùng lại, còn chưa có thì tự sinh ID mới theo định dạng req- + 8 ký tự hex (dùng uuid.uuid4().hex[:8]). Correlation ID này được bind vào context structlog qua bind_contextvars(correlation_id=correlation_id) và lưu vào request.state.correlation_id, đồng thời trả về trong response header x-request-id và x-response-time-ms.
- **Các metadata được ghi vào structured log:** Được bind trong app/main.py trước dòng log request_received gồm: user_id_hash (băm SHA-256 lấy 12 ký tự đầu), session_id, feature, model, env (lấy từ APP_ENV). Sau khi agent xử lý xong, log response_sent ghi thêm: latency_ms, ttft_ms, tokens_in, tokens_out, cost_usd, quality_score, tool_name, tool_success.
- **Cách bảo đảm PII được scrub trước khi ghi:** Trong app/logging_config.py, em cấu hình processor scrub_event đứng trước JsonlFileProcessor và JSONRenderer. Hàm này duyệt đệ quy qua các giá trị chuỗi trong log để thay thế các mẫu PII (email, điện thoại VN, CCCD, thẻ, hộ chiếu) thành các thẻ che như [REDACTED_EMAIL], [REDACTED_PHONE_VN],... nhờ đó log ghi ra file luôn an toàn.
- **Cách kiểm chứng kết quả:** Chạy script python scripts/validate_logs.py đọc data/logs.jsonl đạt 100/100 điểm với 0 leak PII. Ngoài ra bộ test tests/test_pii.py chạy pytest đều pass đầy đủ các trường hợp.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Em cấu hình API key của project cá nhân day13-k4-l3b-02660 vào file .env. Trong metadata của từng trace đều có correlation_id, user_id_hash, model và tag lab tương ứng với từng request em chạy qua load_test.py.
- **Cấu trúc root/retrieval/generation observations:**
  - Root observation: lab-agent-run (loại agent) bao quát toàn bộ lượt chạy của agent.
  - Span con 1: retrieval (loại retriever) ghi nhận tài liệu tìm thấy, query và doc_count.
  - Span con 2: fake-llm-generate (loại generation) ghi nhận model, số lượng token input/output, chi phí ước tính và liên kết tới prompt version.
- **Cách nối trace với log:** Em dùng chung một mã correlation_id sinh ra từ middleware. Mã này vừa được bind vào structured log, vừa được đưa vào metadata của trace qua hàm propagate_attributes, giúp tra cứu 1-1 giữa file log và Langfuse.
- **Prompt name:** day13-chat (Text prompt với 3 biến {{feature}}, {{docs}}, {{message}})
- **Version/label baseline:** Version 1 có nội dung template gốc, gắn nhãn baseline và ban đầu gắn production.
- **Version/label candidate:** Version 2 thêm câu "Trả lời ngắn gọn và súc tích.", gắn nhãn candidate.
- **Trace ID của mỗi version:**
  - Version 1 (baseline / sau rollback production về v1): `6c1c7f991a47496a189bbe3c56eb2172`
  - Version 2 (candidate / khi promote production sang v2): `71536082643aa4bb3f9a5ea3b19b3b7c`
- **Cách promote và rollback `production`:**
  - Promote: Trên giao diện Langfuse, em chuyển nhãn production từ v1 sang v2. Khi ứng dụng nhận request mới, code tự động lấy version 2 theo nhãn production mà không cần sửa code, trace ghi nhận prompt_version = 2.
  - Rollback: Khi cần quay lại, em chuyển nhãn production về lại v1 trên Langfuse. Ứng dụng tự động chuyển về dùng prompt v1, các trace tiếp theo ghi nhận prompt_version = 1.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng đủ 6 panel theo hợp đồng config/dashboard.yaml:
  1. Latency percentiles and TTFT (đơn vị: ms, ngưỡng P95 <= 3000ms)
  2. Request traffic (đơn vị: req/phút, ngưỡng >= 1 rpm)
  3. Error rate and retrieval success (đơn vị: %, ngưỡng error rate <= 2%)
  4. Cost over time (đơn vị: USD, ngưỡng tổng <= $2.50)
  5. Input and output tokens (đơn vị: tokens, ngưỡng tổng <= 50,000)
  6. Quality proxy (đơn vị: score 0 đến 1, ngưỡng trung bình >= 0.75)
- **SLO và lý do chọn:** Em đặt mục tiêu SLO là 99.5% requests thành công và có latency_ms <= 3000ms trong chu kỳ 28 ngày. Mức 3000ms được chọn vì thời gian phản hồi bình thường chỉ khoảng 450-850ms, con số 3000ms là đủ rộng để xử lý khi RAG tải nặng mà vẫn không làm người dùng chờ quá lâu.
- **Cách tính error budget:** Với SLO 99.5%, error budget là 0.5%. Nếu trong 28 ngày có 10,000 requests thì số request tối đa được phép bị chậm hơn 3000ms hoặc bị lỗi là: 10,000 x 0.5% = 50 requests.
- **Ba alert và runbook tương ứng:**
  1. HighLatencyP95 (Warning): Kích hoạt khi p95(latency_ms) > 3000ms trong 5 phút. Runbook tại docs/alerts.md#alert-1.
  2. HighErrorRate (Critical): Kích hoạt khi tỷ lệ lỗi > 2% hoặc tỷ lệ retrieval thành công < 90% trong 3 phút. Runbook tại docs/alerts.md#alert-2.
  3. LowQualityScore (Warning): Kích hoạt khi điểm chất lượng trung bình < 0.75 trong 5 phút. Runbook tại docs/alerts.md#alert-3.

## 7. Điều tra challenge

- **Challenge ID:** day13-k4-l3b-monitoring-llmops-v1
- **Khoảng thời gian điều tra:** 03:59:50Z – 04:00:05Z (10:59:50 – 11:00:05 GMT+7, ngày 30/09/2026)
- **Triệu chứng từ metrics:** Panel Latency percentiles and TTFT ghi nhận độ trễ P95 tăng vọt từ mức baseline 846.5ms lên 3,154.7ms, vượt ngưỡng SLO 3000ms và hiện cảnh báo ALERT. Trong khi đó, TTFT P95 vẫn giữ nguyên ở mức 50.0ms, cho thấy mô hình không bị chậm khi sinh token đầu tiên.
- **Log line và correlation ID liên quan:**
  - correlation_id: req-06c51fca (nằm trong nhóm 5 request bị chậm gồm req-06c51fca, req-7819dcaa, req-b593aae3, req-5ba1543f, req-036027e1)
  - Log line trích xuất từ data/logs.jsonl:
    ```json
    {"ts":"2026-09-30T03:59:50.197801Z","level":"info","event":"response_sent","correlation_id":"req-06c51fca","service":"api","user_id_hash":"96d66e746a58","session_id":"k4-l3b-challenge-s01","feature":"monitoring","latency_ms":3455,"ttft_ms":50,"tool_name":"retrieval","tool_success":true}
    ```
- **Trace ID và span gây ảnh hưởng:**
  - Trace ID: a94334b3762fa55f2c6c313fab215d12 (ứng với correlation_id req-06c51fca).
  - Span gây ảnh hưởng: Span con retrieval mất tới 2.500s (chiếm phần lớn thời gian request), trong khi span fake-llm-generate chỉ mất 0.150s.
- **Root cause:** Thành phần tìm kiếm tài liệu retrieval (Vector DB / cơ sở tri thức) bị nghẽn làm phát sinh độ trễ thêm 2.5 giây đối với các câu hỏi thuộc nhóm feature monitoring (do sự cố rag_slow).
- **Fix action:**
  - Tắt sự cố cản trở bằng lệnh python scripts/inject_incident.py --disable để đưa hệ thống về trạng thái bình thường.
  - Thiết lập cơ chế cache kết quả tìm kiếm (semantic cache) cho các tài liệu hay truy vấn thuộc nhóm monitoring.
  - Kiểm tra và nâng cấp cấu hình tài nguyên cho cụm vector store.
- **Preventive measure:**
  - Cài đặt timeout tối đa 1.5s cho bước retrieval kèm circuit breaker; nếu tìm kiếm quá thời gian thì tự động fallback sang tập tài liệu tĩnh để không làm treo request của người dùng.
  - Bổ sung thêm metric và alert cảnh báo sớm khi retrieval_latency_p95 > 1000ms để phát hiện suy thoái trước khi vi phạm ngưỡng SLO tổng thể.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Em chia nhỏ cây trace thành 3 observation riêng biệt (lab-agent-run làm root, retrieval làm retriever, fake-llm-generate làm generation) thay vì để một span duy nhất. Nhờ tách bạch như vậy, khi gặp sự cố em nhìn vào là thấy ngay bước retrieval tốn 2.5s mà không cần phải đoán mò hay ngồi debug từng dòng code.
- **Một lỗi/blocker đã gặp:** Em gặp lỗi NameError: name 'get_langfuse_client' is not defined trong hàm lifespan khi tắt server ở app/main.py.
- **Cách tìm nguyên nhân và xử lý:** Em đọc traceback trong terminal, thấy hàm get_langfuse_client chưa được import vào main.py. Em đã sửa bằng cách dùng hàm flush_traces() từ module app.tracing để đảm bảo đẩy hết trace lên cloud trước khi tắt ứng dụng.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - Metrics cho em cái nhìn bao quát xem hệ thống có đang khoẻ không, giúp phát hiện thời điểm xảy ra sự cố (ví dụ P95 latency vượt ngưỡng).
  - Logs giúp em tìm ra request cụ thể nào bị ảnh hưởng và lấy được correlation_id cùng thông tin ngữ cảnh.
  - Traces giúp em đi sâu vào cấu trúc bên trong của request đó, xem từng hàm và span chạy hết bao nhiêu giây để chỉ ra đúng nguyên nhân gốc rễ.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Quản lý prompt version giúp đổi prompt linh hoạt thông qua nhãn production/candidate mà không cần deploy lại code. Theo dõi token và cost giúp kiểm soát chi phí gọi mô hình không bị tăng đột biến. SLO và rollback là tấm khiên bảo vệ người dùng, giúp nhanh chóng khôi phục hệ thống khi phiên bản mới gặp trục trặc.
- **Điều quan trọng nhất đã học:** Em học được quy trình hoàn chỉnh để vận hành một ứng dụng AI an toàn và tin cậy: từ việc giấu PII trong log, gán correlation ID xuyên suốt, đến việc dựng trace để quan sát nội tại hệ thống và đặt alert theo dõi SLO.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Điểm chất lượng câu trả lời hiện tại mới dùng hàm heuristic đơn giản; nếu phát triển tiếp em muốn tích hợp đánh giá bằng một mô hình LLM độc lập (LLM-as-a-judge) hoặc thu thập phản hồi like/dislike trực tiếp từ người dùng.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
