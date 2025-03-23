from concurrent import futures
import time
import grpc
import logging_service_pb2
import logging_service_pb2_grpc

messages = {}

class LoggingServiceServicer(logging_service_pb2_grpc.LoggingServiceServicer):
    def LogMessage(self, request, context):
        if request.id in messages:
            detail = "Повідомлення з таким ID вже існує"
        else:
            messages[request.id] = request.msg
            detail = "Повідомлення успішно збережено"
            print(f"Отримано повідомлення: {request.msg} з id: {request.id}")
        return logging_service_pb2.LogResponse(detail=detail)

    def GetLogs(self, request, context):
        logs = list(messages.values())
        return logging_service_pb2.LogsResponse(logs=logs)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    logging_service_pb2_grpc.add_LoggingServiceServicer_to_server(LoggingServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC logging-service запущено на порту 50051")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
