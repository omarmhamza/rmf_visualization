from ast import Call
from re import sub
from threading import Thread
import tkinter as tk
from tkinter.filedialog import asksaveasfile
from typing import Callable, List 
from rclpy.node import Node, Publisher, Subscription
from rmf_task_msgs.msg import BidNotice, BidResponse
from rmf_fleet_msgs.msg import FleetState
import rclpy
from datetime import datetime
import requests, time

class Table(tk.Frame):
    def __init__(self,parent,header_data: List[str]):
        super().__init__(parent)
        self.raw = []
        self.__cols_num = len(header_data)
        self.__header_gen = lambda t: tk.Label(self, text=t , borderwidth=1, relief="solid", width=20, height=2, background="gray")
        self.__label_gen = lambda t: tk.Label(self, text=t , borderwidth=0.5, relief="solid", width=20, height=2)
        self.__table_data = []
        self.insert_row(*header_data)


    def insert_row(self, *args):
        cols_data = []
        for c in range(self.__cols_num):
            text = args[c] if len(args) > c else ""
            if(len(self.__table_data)== 0):
                cell_label = self.__header_gen(text)
                # x = tk.Label()
                # x.get()
            else:
                cell_label = self.__label_gen(text)
            cell_label.grid(row=len(self.__table_data), column=c)
            cols_data.append(cell_label)
        self.__table_data.append(cols_data)
        self.raw.append(cols_data)

    def export_csv(self):
        file = asksaveasfile(filetypes = [('csv', '*.csv')], defaultextension = '.csv')
        rows = ""
        for i in self.__table_data:
            col_count = len(i)
            for index,j in enumerate(i):
                rows = rows + str(j.cget("text"))
                if index < col_count - 1:
                    rows = rows + ','
            rows = rows  + "\n"
        if file:
            file.write(rows)
            print("exported:",rows)

        
class Listener(Node):
    def __init__(self, on_bid_notice: Callable,on_bid_response: Callable, on_task_update: Callable):
        super().__init__('listener')
        self.completed_task_ids = []
        self.history = []
        self.tracker = {}
        self.on_task_update = on_task_update
        self.bid_notice_sub: Subscription = self.create_subscription(BidNotice,'/rmf_task/bid_notice',on_bid_notice,10)
        self.bid_response_sub: Subscription = self.create_subscription(BidResponse,'/rmf_task/bid_response',on_bid_response,10)
        self.fleet_states_sub: Subscription = self.create_subscription(FleetState, '/fleet_states',self.track_task,10)
    
    def track_task(self,msg):
        for robot in msg.robots:
            assigned = self.tracker.get(robot.name,None)
            current_task = robot.task_id 
            if(assigned):
                current_task  = assigned.get('task_id')
            if robot.task_id == "" and assigned or current_task != robot.task_id:
                task_id = self.tracker[robot.name]["task_id"]
                if task_id not in self.completed_task_ids:
                    self.completed_task_ids.append(task_id)
                    self.tracker[robot.name]["finished"] = datetime.utcnow()
                    self.history.append(self.tracker[robot.name])
                    self.on_task_update(self.tracker[robot.name])
                    self.tracker.pop(robot.name)
                    print("HERE--->",self.history)

                # self.tracker.pop(robot.name)
            elif robot.task_id != "" and robot.name not in self.tracker:
                self.tracker[robot.name] = {
                    "task_id": robot.task_id,
                    "started": datetime.utcnow(),
                    "finished": None
                }
                self.on_task_update(self.tracker[robot.name])



class TaskSubmitter:
    def __init__(self) -> None:
        self.___queue = []

    def add_task_to_queue(self, l1,l2):
        task_request = {"task_type":"Loop","start_time":0,"priority":0,"description":{"num_loops":1,"start_name":l1,"finish_name":l2}}
        self.___queue.append(task_request)
        return self
    
    def submit_tasks(self):
        for task in self.___queue:
            requests.post(url="http://localhost:8083/submit_task",json=task)
            print("Sent Task: {}".format(task.get('description','')))
            time.sleep(0.5)

    def submit_tasks_async(self):
        Thread(target=self.submit_tasks).start()

    def clear_tasks(self):
        self.___queue.clear()






class Window:
    def __init__(self) -> None:
        self.root = None
        self.content_frame = None
        self.implementation()

    def implementation(self):
        self.root = tk.Tk()
        self.root.title("Task Allocation")
        self.root.geometry("1200x500")
        # Create A Main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH,expand=1)
        # Create Frame for X Scrollbar
        sec = tk.Frame(main_frame)
        sec.pack(fill=tk.X,side=tk.BOTTOM)
        # Create A Canvas
        main_canvas = tk.Canvas(main_frame)
        main_canvas.pack(side=tk.LEFT,fill=tk.BOTH,expand=1)
        x_scrollbar = tk.Scrollbar(sec,orient=tk.HORIZONTAL,command=main_canvas.xview)
        x_scrollbar.pack(side=tk.BOTTOM,fill=tk.X)
        y_scrollbar = tk.Scrollbar(main_frame,orient=tk.VERTICAL,command=main_canvas.yview)
        y_scrollbar.pack(side=tk.RIGHT,fill=tk.Y)
        # Configure the canvas
        main_canvas.configure(xscrollcommand=x_scrollbar.set)
        main_canvas.configure(yscrollcommand=y_scrollbar.set)
        main_canvas.bind("<Configure>",lambda e: main_canvas.config(scrollregion= main_canvas.bbox(tk.ALL)))
        # Create Another Frame INSIDE the Canvas
        self.content_frame = tk.Frame(main_canvas)
        # Add that New Frame a Window In The Canvas
        main_canvas.create_window((0,0),window= self.content_frame, anchor="nw")


if __name__ == "__main__":
    window = Window()
    table_widget = Table(window.content_frame, header_data=["Task Id", "Accepted", "Fleet", "Robot", "Prev Cost", "New Cost", "Dipatch Time", "Start Time", "Finish Time"])
    table_widget.pack(fill="both", expand=True)
    # btn = tk.Button(window.content_frame, text='export csv',command=table_widget.export_csv)
    # btn.pack(side='top')
    def on_save(event):
        table_widget.export_csv()
    window.root.bind("<Control-s>", on_save)
    rclpy.init()
    def on_bid_notice(msg):
        pass


    def on_bid_response(msg: BidResponse):
        row = [msg.task_id, msg.has_proposal, msg.proposal.fleet_name, msg.proposal.expected_robot_name,msg.proposal.prev_cost,msg.proposal.new_cost,str(datetime.utcnow())]
        table_widget.insert_row(*row)

    def on_update(data):
        task_id = data.get('task_id','')
        started = data.get('started',None)
        finished = data.get('finished',None)
        # print("done",started)
        if not task_id:
            return
        for row in table_widget.raw:
            for col in reversed(row): ## get latest cost
                if str(col.cget("text")) == task_id:
                    new_row = []
                    for col in row:
                        text = str(col.cget("text"))
                        if text == "":
                            continue
                        new_row.append(text)
                    new_row.append(str(started))
                    new_row.append(str(finished))
                    # print(new_row)
                    table_widget.insert_row(*new_row)
                    return

    listener = Listener(on_bid_notice,on_bid_response,on_update)
    Thread(target=rclpy.spin, args=[listener]).start()
    submitter = TaskSubmitter()
    submitter.add_task_to_queue("load1","load2")
    submitter.add_task_to_queue("load5","load6")
    submitter.add_task_to_queue("load7","load8")
    submitter.add_task_to_queue("load5","load4")
    submitter.add_task_to_queue("load9","load8")
    submitter.add_task_to_queue("load7","load1")
    submitter.add_task_to_queue("load6","load3")
    submitter.add_task_to_queue("load4","load9")
    submitter.add_task_to_queue("load5","load2")
    submitter.add_task_to_queue("load4","load7")
    submitter.add_task_to_queue("load4","load7")
    submitter.add_task_to_queue("load11","load10")
    submitter.add_task_to_queue("load2","load5")
    submitter.add_task_to_queue("load8","load5")
    submitter.add_task_to_queue("load6","load8")
    submitter.add_task_to_queue("load9","load3")
    submitter.add_task_to_queue("load13","load12")
    submitter.add_task_to_queue("load14","load12")

    submitter.submit_tasks_async()
    window.root.mainloop()
    listener.destroy_node()
    rclpy.shutdown()