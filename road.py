import car
import generate
import sys
import math

import random
from statistics import harmonic_mean

class RoadManager(object):
    """
    道路を管理するクラス。このクラスを呼んでインスタンスを作ること。
    """
    def __init__(self,time_max):
        self.roadlist = []
        self.road_id = 0
        self.time_max = time_max

    def append(self,road_param):
        road = Road(self.road_id,self.time_max,**road_param)
        self.roadlist.append(road)

        self.road_id += 1

    def get_list(self):
        return self.roadlist

class Road(object):
    """
    道路の本体。道路にパラメータを持たせる場合はここを編集する
    """
    def __init__(self,
                 road_id,
                 time_max,
                 queue,
                 generate_time_max,
                 vel_hope_max,
                 road_length,
                 sag,
                 ratio_type,
                 jam_prevision_vel,
                 ic_pos,
                 seed
                 ):

        #車線数チェック
        if len(queue) != len(vel_hope_max):
            print("[ERROR]交通量と希望速度の車線数が合いません。")
            sys.exit()

        #id
        self.id = road_id

        #seed値
        self.seed = seed

        #車両IDスタート値
        self.start_carID = road_id * 10000

        #今走っている車のidリスト
        self.run_car_list = []

        #各車線の交通量タプル
        self.queue = queue

        #車両台数の合計
        self.car_max = sum(self.queue)

        #車の発行所を作成(generate_carメソッドで実際に生成するときに使用)
        self.carcreater = car.CarCreater(   start_id = self.start_carID,
                                            car_max = self.car_max,
                                            seed = seed)

        #車両発生台数からどれくらいの間隔で車両を発生させるかのテーブルを作成
        self.gen_time = generate.generate_car_timetable(queue,
                                                        generate_time_max,
                                                        seed)

        #最後尾が発生位置からどれだけ離れたら車両を発生させるかのテーブルを作成
        self.gen_ss = generate.generate_car_sstable(queue)

        #道路の長さ
        self.road_length = road_length

        #最大希望速度
        self.vel_hope_max = vel_hope_max

        #最後尾の車両を保持するための変数宣言
        self.last_car = [None] * len(queue)

        #サグ部に関する情報を保存する辞書
        if sag["start"] > sag["end"]:
            print("[ERROR]サグ部の位置が不正です。")
            sys.exit()
        self.sag = sag

        #typeの割合
        if sum(ratio_type) != 1:
            print("[ERROR]type割合の合計が不正です。")
            sys.exit()
        self.ratio_type = ratio_type

        #typeそれぞれ何台発生したか記録するリスト
        self.sum_type = [0] * len(self.ratio_type)

        #アグレッシブドライバーが何台発生したか記録するリスト
        self.sum_ag_driver = 0

        #車線ごとに前方位置順に車両IDを並べた二次元リスト
        self.lane_lists = [[] for i in range(len(self.queue))]

        #IC位置のタプル【山内卒論】
        self.ic_pos = ic_pos

        #各IC区間を走る車両の二次元リスト【山内卒論】
        self.ic_section_type0_list = [[] for i in range(len(self.ic_pos))]

        # #IC区間の交通量のリスト【山内卒論】
        # self.ic_q = [0] * self.ic_pos

        #渋滞予見車両のリスト【山内卒論】
        self.jam_prevision_type0_list = []

        #渋滞迂回車両の台数【山内卒論】
        self.sum_ic_out_car = [0] * len(self.ic_pos)

        #渋滞予見速度閾値【山内卒論】
        self.jam_prevision_vel = jam_prevision_vel

        #目標交通量保持【渡邊修論】
        #self.target_q = None

        #迂回車両id記録【渡邊修論】
        self.detour_list = []

        #迂回制御開始時間記録
        self.start_control_time = None

        #一般道路旅行時間推定用パラメータ【渡邊修論】
        if road_id == 1:
            #待ち行列用プログラムで算出したパラメータを設定
            self.a_param = 0.030729
            self.b_param = 26.52083

            #パラメータ算出時に使用した距離を設定
            self.queuing_distance = 500

            #交通容量設定
            self.vol_capacity = 2250

        #迂回制御終了時刻
        self.avoid_end_time = -1

        #迂回制御中フラグ
        self.avoid_flag = False

        #迂回IC
        self.avoid_ic = None

        #迂回時間カウンタ
        self.detour_time_count = 0

    def update_lane_lists(self):
        '''
        run_car_listからlane_listsを更新
        '''
        for lane_i in range(len(self.lane_lists)):
            self.lane_lists[lane_i] = []

        for run_car in self.run_car_list:
            lane_no = run_car.lane
            self.lane_lists[lane_no].append(run_car)
        
        for lane_i in range(len(self.lane_lists)):
            self.lane_lists[lane_i].sort(key=lambda x:x.front,reverse=True)

    def update_last_car(self):
        '''
        最後尾車両の情報を更新
        '''

        for lane_i,lane_list in enumerate(self.lane_lists):
            if len(lane_list) == 0:
                self.last_car[lane_i] = None
            else:
                self.last_car[lane_i] = self.lane_lists[lane_i][-1]

    def update_car_info(self,time):
        '''
        走行中の全車両に対して加速度以外の情報を更新

        【山内卒論】【渡邊修論】
        渋滞が予見された場合、予見された位置をメンバ変数に保存
        '''

        self.ic_section_type0_list = [[] for i in range(len(self.ic_pos))]
        self.jam_prevision_type0_list = []

        for run_car in self.run_car_list:#車両の数だけループ

            #位置更新
            run_car.cal_pos()

            #速度更新
            run_car.cal_vel()

            #鈍化状態更新
            run_car.update_dull_state()

            #これ以降type0車両のみの処理
            if run_car.type != 0:
                continue

            #最寄りIC更新【山内卒論】【渡邊修論】
            run_car.update_nearest_ic(self)
            if run_car.nearest_ic != None:
                self.ic_section_type0_list[run_car.nearest_ic].append(run_car)

            #渋滞予見【山内卒論】【渡邊修論】
            run_car.jam_prevision()
            if run_car.jam_prevision_flag:
                self.jam_prevision_type0_list.append(run_car)

    def detour_control_yamauchi(self,time,target_vol,detour_road,avoiding_sec):

        def search_avoid_ic(num_border):
            
            avoid_ic = None

            if len(self.jam_prevision_type0_list) > num_border:
                jam_prevision_pos_list = [car.front for car in self.jam_prevision_type0_list]
                min_distance_ic = float("infinity") #初期値
                for ic_i,ic_pos in enumerate(self.ic_pos):
                    distance_ic = min(jam_prevision_pos_list) - ic_pos
                    if 0 < distance_ic < min_distance_ic:
                        min_distance_ic = distance_ic
                        avoid_ic = ic_i
            return avoid_ic

        def cal_ic_section_q(ic_i):

            #迂回IC区間の平均速度(調和平均)
            avoid_ic_section_vel_list = [car.vel for car in self.ic_section_type0_list[ic_i]]

            #車両生成をしなくなると後方の車両が居なくなるため，その場合は迂回制御をしない
            if len(avoid_ic_section_vel_list) == 0:
                return

            avoid_ic_section_vel_ave = harmonic_mean(avoid_ic_section_vel_list)

            #迂回IC区間の距離
            if ic_i == 0:
                avoid_ic_section_len = self.ic_pos[ic_i]
            else:
                avoid_ic_section_len = self.ic_pos[ic_i] - self.ic_pos[ic_i-1]

            #迂回IC区間の密度
            #交通量は1車線として考えるため2で割る
            avoid_ic_section_den_ave = (len(self.ic_section_type0_list[ic_i]) / 2) / avoid_ic_section_len / self.ratio_type[0]

            #迂回IC区間の時間交通量
            avoid_ic_section_q = avoid_ic_section_den_ave * avoid_ic_section_vel_ave * 3600 

            return avoid_ic_section_q

        def detour_cars(delete_type0_per):
            for run_car in self.run_car_list:
                if run_car.type != 0:
                    continue

                if not (self.ic_pos[self.avoid_ic] > run_car.front > self.ic_pos[self.avoid_ic] - 200):
                    continue

                #乱数テーブルリセット。時間,車両IDと乗算することで、各時間,各車両ごとに疑似的に乱数を再現
                random.seed(self.seed * time * run_car.car_id)

                if random.random() < delete_type0_per:

                    if run_car.change_detour(detour_road,time):

                        #迂回先の走行車両リストに車両インスタンスを追加
                        detour_road.run_car_list += [run_car]                
                        #元の車線から車両削除
                        self.run_car_list.remove(run_car)
                        #迂回した車両を記録
                        self.detour_list.append(int(run_car.car_id))
                        #迂回車両台数をカウント
                        self.sum_ic_out_car[self.avoid_ic] += 1

        #目標交通量が0以下であればリターン
        if target_vol <= 0:
            return

        #迂回制御終了処理
        if self.avoid_flag == True and time >= self.avoid_end_time:
            #self.avoid_flag = False
            self.avoid_flag = None
            #self.avoid_end_time = -1

        #迂回制御が終了していたらリターン
        if self.avoid_flag == None:
            return

        #迂回制御フラグが落ちており，渋滞予見車両が5台以上のとき直前のICを探し、迂回ICとする
        if self.avoid_flag == False:
            self.avoid_ic = search_avoid_ic(5)

        #迂回ICがなければリターン(渋滞予見フラグ閾値未満を含む)
        if self.avoid_ic == None:
            return

        #迂回制御開始処理
        if self.avoid_flag == False:
            self.avoid_flag = True
            self.avoid_end_time = time + avoiding_sec * 10

            #初回のみ迂回制御開始時間記録
            if self.start_control_time is None:
                self.start_control_time = time / 10

        #迂回制御時間をカウント
        self.detour_time_count += 1

        #迂回IC区間の交通量計算
        avoid_ic_section_q = cal_ic_section_q(self.avoid_ic)

        #目標交通量を設定
        # if self.target_q == None:
        #     self.target_q = target_vol
        target_q = target_vol

        #迂回IC区間の交通量が目標交通量を下回っていたらリターン
        if avoid_ic_section_q <= target_q:
            return
            
        #削減率を計算
        delete_per = (avoid_ic_section_q - target_q) / avoid_ic_section_q

        #type0削減率を計算
        if self.ratio_type[0] > delete_per:
            delete_type0_per = delete_per / self.ratio_type[0]
        else:
            delete_type0_per = 1

        #IC付近にtype0車両が存在すれば搭載車削減率に応じて道路離脱
        detour_cars(delete_type0_per)

    def update_accl(self):
        '''
        走行中の全車両に対してIDMなどから加速度を計算し更新
        '''
        for run_car in self.run_car_list:#車両の数だけループ
            #前の車のIDと車間,相対速度を調べる関数
            run_car.relative_front_car(self.lane_lists)

            ##ここから加速度更新
            run_car.cal_accl(self)
                    
            #ここまで加速度処理

    def change_lane(self,time):
        '''
        走行中の全車両に対して車線変更処理
        '''
        for run_car in self.run_car_list:#車両の数だけループ
            
            #【渡邊修論】迂回車両が走行車線に合流できるか
            if run_car.lane == 0:
                run_car.merge_detour(self,time)
            else:
                #右隣に対する車線変更処理
                run_car.change_lane(self,run_car.lane+1,time)

                #左隣に対する車線変更処理
                run_car.change_lane(self,run_car.lane-1,time)

    def car_add(self,
                time,
                lane,
                inter_vehicle_distance,
                front_car_id,
                ):
        """
        車両生成し、生成した車両を返す
        generate_carのサポートメソッド
        """
        
        # #初期速度を固定 制限速度を基準にして設定する。希望速度がこの値以上なら車両追従の式で速度が上がっていく
        # v_clbr = v_init_clbr/3.6
        # v_init = self.vel_hope_max[lane]/3.6 + v_clbr

        #生成する車のパラメータを設定。パラメータを増やす場合はcar.pyとここを編集する。
        car_param = dict(time = time,
                        road_id = self.id,
                        lane = lane,
                        vel_hope = self.vel_hope_max,
                        inter_vehicle_distance = inter_vehicle_distance,
                        front_car_id = front_car_id,
                        ratio_type = self.ratio_type,
                        jam_prevision_vel = self.jam_prevision_vel
                        )

        car_ins = self.carcreater.create(car_param)
        return car_ins

    def generate_car(self,time):
        """
        道路のスタート地点に車両を生成
        """

        for lane_i,lane_list in enumerate(self.lane_lists):
            
            #timetableに何も値がない場合、車両生成を行わない
            if (len(self.gen_time[lane_i]["timetable"])==0 or 
                len(self.gen_ss[lane_i]["timetable"])==0
                ):
                continue
            
            #各timetableのnext値がテーブルの長さを越えている場合、車両生成を行わない
            nextNo = self.gen_ss[lane_i]["next"]
            if (nextNo >= len(self.gen_time[lane_i]["timetable"]) or 
                nextNo >= len(self.gen_ss[lane_i]["timetable"])
                ):
                continue

            if self.last_car[lane_i] is None:
                last_car_back = float("infinity")
            else:
                last_car_back=self.last_car[lane_i].back

            #車両生成条件
            if (time >= self.gen_time[lane_i]["timetable"][nextNo] and 
                last_car_back >= self.gen_ss[lane_i]["timetable"][nextNo] and
                self.carcreater.nextCntcheck() < self.car_max
                ):
                if len(lane_list) == 0:
                    front_car_id = -1
                    inter_vehicle_distance = float("infinity")
                else:
                    front_car_id = self.last_car[lane_i].car_id
                    inter_vehicle_distance = last_car_back

                car_ins = self.car_add( time = time,
                                        lane = lane_i,
                                        inter_vehicle_distance = inter_vehicle_distance,
                                        front_car_id = front_car_id,
                                        )

                self.sum_type[car_ins.type] += 1
                if car_ins.is_aggressive_driver:
                    self.sum_ag_driver += 1

                #走行車両リストに車両インスタンスを追加
                self.run_car_list += [car_ins]
                
                #各timetableのnext値を更新
                self.gen_time[lane_i]["next"]+=1
                self.gen_ss[lane_i]["next"]+=1

    def remove_car(self,time,traveltime_list):
        """
        道路の終端を越えた車両を削除
        削除時に車両の生存時間(=旅行時間)を記録
        """
        for run_car in self.run_car_list:
            if run_car.front > self.road_length:#前方位置
                #旅行時間記録
                generate_time = run_car.generate_time / 10
                remove_time   = time / 10
                life_time = remove_time - generate_time

                if run_car.detour_info == "highway":

                    travel_info = dict( car_id = run_car.car_id,
                                        generate_time = generate_time,
                                        remove_time = remove_time, 
                                        life_time = life_time)
                    traveltime_list["highway"].append(travel_info)
                elif run_car.detour_info == "general":

                    travel_info = dict( car_id = run_car.car_id,
                                        generate_time = generate_time,
                                        remove_time = remove_time, 
                                        life_time = life_time)
                    traveltime_list["general"].append(travel_info)
                elif run_car.detour_info == "detour":

                    travel_info = dict( car_id = run_car.car_id,
                                        generate_time = generate_time,
                                        remove_time = remove_time, 
                                        life_time = life_time)
                    traveltime_list["detour"].append(travel_info)
                else:
                    if run_car.detour_info != "pre-detour":
                        raise NotImplementedError("迂回情報に想定外の値が入っています。")

                self.run_car_list.remove(run_car)