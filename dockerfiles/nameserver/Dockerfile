FROM python:3.6-alpine

RUN pip install Pyro4 dill

ENV PYRO_SERIALIZERS_ACCEPTED=serpent,json,marshal,pickle,dill
ENV PYTHONUNBUFFERED=0

ENTRYPOINT ["pyro4-ns", "-n", "nameserver"]

EXPOSE 9090
