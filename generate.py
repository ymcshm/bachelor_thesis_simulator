import random
import numpy as np
import car

def generate_random(per):#引数は1を生成する確率[%]
    """
    与えた引数(単位:パーセント)の確率で1を生成する。resolutionは1%。
    ex:引数に45.6を与えた場合、45%の確率で1が生成される。
    """
    x=random.randint(1,100)
    if x>per:
        return 0
    else:
        return 1

def generate_car_timetable(queue,
                           time_max,
                           seed):

    #車両の発生間隔設定
    def cal_frequency(q_lane):
        if q_lane<=0: 
            res=float("infinity")#発生台数0の時は、ありえない発生間隔に設定
        else:
            res = time_max/q_lane#車両発生間隔=最大時間/加速車線の最大台数(例:600秒/100台=6秒に1回に発生)


        #発生間隔をランダムにする
        res += res * round(random.uniform(-0.25,0.25),2)
        # res += res * round(random.uniform(-0.5,0.5),2)
        res = round(res)
        
        return res

    #timetableを作成する
    def make_gentimetable_lane(q_lane):
        gentimetable_lane = np.zeros(q_lane)
        for car_i in range(len(gentimetable_lane)):
            if car_i != 0:
                gentimetable_lane[car_i] = gentimetable_lane[car_i-1] + cal_frequency(q_lane)
        return gentimetable_lane

    #乱数テーブルリセット
    random.seed(seed)

    gen_timetable = []
    for q_lane in queue:
        #gentimetable_lane = np.zeros(q_lane)
        #frequency_lane = cal_frequency(q_lane)
        gentimetable_lane = dict(timetable = make_gentimetable_lane(q_lane), next = 0)
        gen_timetable.append(gentimetable_lane)

    return gen_timetable

#車間距離テーブル固定値版
def generate_car_sstable(queue):

    #timetableを作成する
    def make_gensstable_lane(q_lane):
        gensstable_lane = np.zeros(q_lane)
        for time_i in range(len(gensstable_lane)):
            gensstable_lane[time_i] = 0
        return gensstable_lane

    gen_sstable = []
    for q_lane in queue:
        #gensstable_lane = np.zeros(q_lane)
        gensstable_lane = dict(timetable = make_gensstable_lane(q_lane), next = 0)
        gen_sstable.append(gensstable_lane)

    return gen_sstable