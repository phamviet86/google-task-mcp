# Google Tasks MCP — Bắt đầu nhanh

`google-task-mcp` là kho mã nguồn. Lệnh MCP là `google-tasks-mcp` và
`google-tasks-mcp-auth`. Tên gói Python dành cho dự án này là
`phamviet-google-tasks-mcp`; **không** cài `google-tasks-mcp` từ PyPI vì đó là gói không liên quan.

Hiện kho chưa có Git tag hoặc GitHub Release. Vì vậy chưa có bản `0.3.0` để tải/cài chính thức. Khi
có GitHub Release, tải wheel đúng phiên bản, kiểm tra checksum, rồi cài trong môi trường riêng:

```bash
uv venv --python /usr/bin/python3.12 /opt/google-tasks-mcp/venv
uv pip install --python /opt/google-tasks-mcp/venv/bin/python \
  /duong-dan/an-toan/phamviet_google_tasks_mcp-0.3.0-py3-none-any.whl
```

Trong Google Cloud, bật **Google Tasks API**, tạo OAuth client loại **Desktop app**, và lưu file JSON
ngoài kho mã. Xác thực trên máy chạy MCP:

```bash
GOOGLE_TOKEN_FILE=/duong-dan/an-toan/google-tasks/token.json \
  /opt/google-tasks-mcp/venv/bin/google-tasks-mcp-auth \
  --client-secret /duong-dan/an-toan/client_secret.json
```

Sau đó cấu hình MCP client bằng đường dẫn tuyệt đối đến
`/opt/google-tasks-mcp/venv/bin/google-tasks-mcp`, và truyền cùng biến `GOOGLE_TOKEN_FILE`.

Máy chủ chỉ dùng `stdio`, không mở cổng mạng, không có cơ sở dữ liệu hoặc tiến trình nền. Có thể khởi
tạo MCP và xem 14 tools khi chưa xác thực; lần gọi tool đầu tiên sẽ báo lỗi xác thực cho đến khi tạo
token. macOS và Linux được hỗ trợ; Windows chưa được kiểm chứng.

Xem hướng dẫn đầy đủ bằng tiếng Anh: [README.md](README.md) và
[triển khai/phát hành](docs/release-deployment.md).
