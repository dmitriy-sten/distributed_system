import threading
import time
import hazelcast


#Distributed Map Demo

def distributed_map_demo(client):
    print("\n--- Distributed Map Demo: Запис 1000 элементів ---")
    dmap = client.get_map("distributed-map").blocking()
    for i in range(1000):
        dmap.put(i, f"value-{i}")
        if i % 100 == 0:
            print(f"Записано {i} элементів...")
    print("Записано 1000 элементів в Distributed Map.")




#Concurrent Increment без блокувань (No Lock)
def concurrent_increment_no_lock(client):
    print("\n--- Concurrent Increment без блокувань ---")
    dmap = client.get_map("concurrent-map-no-lock").blocking()

    dmap.put("key", 0)

    def increment_no_lock():
        for _ in range(10_000):
            current = dmap.get("key")
            dmap.put("key", current + 1)

    threads = []
    for i in range(3):
        t = threading.Thread(target=increment_no_lock, name=f"NoLock-Thread-{i+1}")
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    final_value = dmap.get("key")
    print(f"Фінальне значення (без блокувань): {final_value}")
    print("Очікуване значення: 30000")


# Increment з песимістичним блокуванням
def concurrent_increment_with_lock(client):
    print("\n--- Concurrent Increment з песимістичним блокуванням ---")
    dmap = client.get_map("concurrent-map-lock").blocking()
    dmap.put("key", 0)

    def increment_with_lock():
        for _ in range(10_000):
            dmap.lock("key")
            try:
                current = dmap.get("key")
                dmap.put("key", current + 1)
            finally:
                dmap.unlock("key")

    threads = []
    start_time = time.time()
    for i in range(3):
        t = threading.Thread(target=increment_with_lock, name=f"Lock-Thread-{i+1}")
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    end_time = time.time()

    final_value = dmap.get("key")
    print(f"Фінальне значення (песимістичне блокування): {final_value}")
    print(f"Час виконання: {end_time - start_time:.3f} сек")
    print("Очікуване значення: 30000")


#Increment з оптимістичним блокуванням (CAS)
def concurrent_increment_with_cas(client):
    print("\n--- Concurrent Increment з оптимістичним блокуванням (CAS) ---")
    dmap = client.get_map("concurrent-map-cas").blocking()
    dmap.put("key", 0)

    def increment_with_cas():
        for _ in range(10_000):
            while True:
                current = dmap.get("key")
                # replace повертає True, якщо оновлення пройшло успішно
                if dmap.replace("key", current, current + 1):
                    break

    threads = []
    start_time = time.time()
    for i in range(3):
        t = threading.Thread(target=increment_with_cas, name=f"CAS-Thread-{i+1}")
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    end_time = time.time()

    final_value = dmap.get("key")
    print(f"Фінальне значення (CAS): {final_value}")
    print(f"Час виконання: {end_time - start_time:.3f} сек")
    print("Очікуване значення: 30000")


#Bounded Queue
def bounded_queue_demo(client):
    print("\n--- Демонстрація роботи Bounded Queue ---")
    queue = client.get_queue("bounded-queue").blocking()
    
    def producer():
        for i in range(1, 101):
            print(f"Producer: намагаюсь додати {i}...")
            queue.put(i) 
            print(f"Producer: додано {i}")
            time.sleep(0.1) 
        for _ in range(2):
            queue.put(None)
    print('\n')

  
    def consumer(consumer_id):
        count = 0
        while True:
            item = queue.take()  # чекає на доступний елемент
            if item is None:
                print(f"Consumer {consumer_id}: отримано сигнал завершення.")
                break
            print(f"Consumer {consumer_id}: отримано {item}")
            count += 1
            time.sleep(0.15)
        print(f"Consumer {consumer_id}: оброблено {count} елементів.")

  
    prod_thread = threading.Thread(target=producer, name="Producer")
    cons_thread1 = threading.Thread(target=consumer, args=(1,), name="Consumer-1")
    cons_thread2 = threading.Thread(target=consumer, args=(2,), name="Consumer-2")

    prod_thread.start()
    cons_thread1.start()
    cons_thread2.start()

    prod_thread.join()
    cons_thread1.join()
    cons_thread2.join()
    print("\n")



def main():
    client = hazelcast.HazelcastClient(
        cluster_members=["127.0.0.1:5701", "127.0.0.1:5702", "127.0.0.1:5703"]
    
    )
    print("connected")

    # 1. Distributed Map Demo
    # distributed_map_demo(client)
    # input("\nnext-> тест  конкурентного доступу (без блокувань)...")

    # 2. Concurrent Increment без блокувань
    concurrent_increment_no_lock(client)
    input("\nnext-> тест  з песимістичним блокуванням...")

    # 3. Concurrent Increment з песимістичним блокуванням
    concurrent_increment_with_lock(client)
    input("\n next-> тест з оптимістичним блокуванням (CAS)...")

    # 4. Concurrent Increment з оптимістичним блокуванням (CAS)
    concurrent_increment_with_cas(client)
    input("\nnext-> тесту до демонстрації роботи Bounded Queue...")

    # 5. Демонстрація роботи Bounded Queue
    bounded_queue_demo(client)

    client.shutdown()
    print("\n---Done---.")


if __name__ == "__main__":
    main()
