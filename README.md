# Lập thời khóa biểu bằng thuật toán GA - Nhóm 5

Hệ thống lập thời khóa biểu cho một khoa bằng Genetic Algorithm, có Hard/Soft Constraints và baseline Random/Greedy.

## Cấu hình GA demo
population=10, generations=20, mutation=0.05, crossover=0.80, elite=5, tournament=3, seed=42.

## Dataset
Small: 8 lớp, 12 học phần, 8 GV, 6 phòng lý thuyết, 2 LAB.
Medium: 20 lớp, 42 học phần, 28 GV, 15 phòng lý thuyết, 5 LAB.
Large: 50 lớp, 125 học phần, 45 GV, 24 phòng lý thuyết, 6 LAB.

## Chạy backend
```powershell
cd backend
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```
Swagger: http://127.0.0.1:8000/docs

## Chạy frontend
```powershell
cd frontend
npm install
npm run dev
```
