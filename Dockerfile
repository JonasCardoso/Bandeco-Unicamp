FROM python:3.10-slim

WORKDIR /bandeco
COPY . .

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN apt-get update && apt-get install libgl1-mesa-glx -y

ENTRYPOINT ["python3"]
CMD ["src/bot.py"]
