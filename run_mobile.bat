@echo off
echo ========================================================
echo 🍎 과일대장 24시간 자동화 ^& 모바일 원격 접속 서버 시작 🍏
echo ========================================================
echo.
echo [1] 과일대장 웹 서버(Streamlit)를 백그라운드에서 실행합니다...
start /b streamlit run app.py

echo.
echo [2] 스마트폰 접속용 공개 URL(터널링)을 생성합니다... (잠시만 기다려주세요)
echo.
echo ⚠️ 경고: 아래에 나타나는 "your url is: https://어쩌구.loca.lt" 주소를
echo 스마트폰 카카오톡이나 브라우저에 복사해 넣으시면 언제 어디서든 접속 가능합니다!
echo.
call npx localtunnel --port 8501
pause
