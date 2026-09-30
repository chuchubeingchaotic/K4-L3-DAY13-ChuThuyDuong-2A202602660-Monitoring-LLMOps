# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Latency P95 của `response_sent.latency_ms` <= 3000ms
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng bị chậm phản hồi, tăng nguy cơ timeout trên client và giảm trải nghiệm người dùng.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở panel *Latency percentiles and TTFT* trên dashboard để xác định thời điểm P95/P99 bắt đầu vượt ngưỡng và giá trị TTFT tương ứng.
  2. **Logs**: Lọc `data/logs.jsonl` với `event == "response_sent"` trong khoảng thời gian xảy ra sự cố, tìm các bản ghi có `latency_ms > 3000` và trích xuất `correlation_id`.
  3. **Traces**: Tìm trace tương ứng với `correlation_id` trên Langfuse, so sánh thời gian của span con `retrieval` và `fake-llm-generate` để xác định bước gây nghẽn (ví dụ: vector store chậm hay model sinh token chậm).
- Mitigation tạm thời: Bật fallback cache cho retrieval, giảm độ dài context tài liệu hoặc rollback prompt về version ổn định hơn nếu do prompt quá dài.
- Owner: `student-2A202602660`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Error rate <= 2% và Retrieval success rate >= 90%
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` hoặc `retrieval_success_rate < 90%` trong 3 phút
- Ảnh hưởng tới người dùng: Người dùng nhận mã lỗi HTTP 500 hoặc câu trả lời không có thông tin chính xác từ tài liệu hỗ trợ.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở panel *Error rate and retrieval success* trên dashboard để kiểm tra số lượng lỗi và tỷ lệ lỗi phân loại theo `error_type`.
  2. **Logs**: Lọc `data/logs.jsonl` tìm các event `request_failed`, kiểm tra trường `error_type` (ví dụ `RuntimeError`), `payload.detail`, và lấy `correlation_id`.
  3. **Traces**: Tra cứu `correlation_id` trên Langfuse, kiểm tra observation `retrieval` bị đánh dấu `ERROR` và xem chi tiết ngoại lệ ("Vector store timeout").
- Mitigation tạm thời: Chuyển hướng retrieval sang kho dữ liệu dự phòng (in-memory corpus / secondary cluster) hoặc trả lời bằng fallback template an toàn.
- Owner: `student-2A202602660`

## Alert 3

- Tên: `LowQualityScore`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Quality proxy trung bình >= 0.75
- Điều kiện và thời gian duy trì: `mean(quality_score) < 0.75` trong 5 phút
- Ảnh hưởng tới người dùng: Câu trả lời ngắn, thiếu thông tin, hoặc chứa dấu hiệu vi phạm định dạng chất lượng.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở panel *Quality proxy* trên dashboard để xem xu hướng điểm chất lượng có giảm dốc hoặc trũng xuống dưới 0.75 không.
  2. **Logs**: Lọc `data/logs.jsonl` tìm `event == "response_sent"` có `quality_score < 0.7`, kiểm tra `payload.answer_preview` và `feature`.
  3. **Traces**: Mở trace trên Langfuse, kiểm tra prompt version đang kích hoạt (`prompt_version`), metadata tài liệu (`doc_count == 0` hay không), và điểm số heuristic gắn kèm trace.
- Mitigation tạm thời: Rollback label prompt `production` về phiên bản prompt trước đó (v1) qua Langfuse UI mà không cần sửa mã nguồn.
- Owner: `student-2A202602660`

