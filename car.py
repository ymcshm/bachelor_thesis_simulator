import random
import numpy as np

from collections import deque
from types import SimpleNamespace

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

class MovingAverage(object):
	'''
    逐次入力に対して移動平均を計算するためのクラス
    '''

	def __init__(self,size):          
		self.pc = 0
        #リングバッファとして使う
		self.data=[0]*size
		self.size=size
		self.full=False

	def put(self,value):
		self.data[self.pc]=value
		self.pc=self.pc+1
		if self.pc==self.size:
			self.pc = 0
			self.full=True
		return self.full

	def average(self):
		if self.full:
			return sum(self.data)/self.size
		else:
			#入力が足りないときにも一応値を返してみる。
			return sum(self.data)/self.pc

class CarCreater(object):
    """
    車を管理するクラス。このクラスを呼んでインスタンスを作ること。
    """
    def __init__(self,start_id,car_max,seed):
        self.next_car_id = start_id
        self.next_cnt = 0
        self.car_seed = seed

    def create(self,car_param):
        car = Car(self.next_car_id,self.car_seed,**car_param)
        self.next_car_id += 1
        self.next_cnt    += 1

        return car

    def nextCntcheck(self):
        return self.next_cnt

class Car(object):
    """
    車の本体。車にパラメータを持たせる場合はここを編集する
    """
    def __init__(self,
                 car_id,
                 seed,
                 time,
                 road_id,
                 lane,
                 vel_hope,
                 inter_vehicle_distance,
                 front_car_id,
                 ratio_type,
                 jam_prevision_vel
                 ):

        #ID
        self.car_id = car_id
        #シード値
        self.seed = seed
        #発生時間
        self.generate_time = time

        #乱数テーブルリセット(seed値*ID*時間で掛けることで、各車両ごとに違う値が振られるようにする)
        random.seed(seed * car_id * time)

        #時間経過で毎回値が変わらないパラメータ
        #最大加速度
        self.max_accl             = round(random.uniform(0.45,0.75),2)
        #希望減速度
        self.desired_Deceleration = round(random.uniform(1.3,1.9),1)
        #反応時間Treac
        self.driver_reaction_time_init = round(random.uniform(0.3,0.4),2)   #初期値
        self.driver_reaction_time_dull = self.driver_reaction_time_init + round(random.uniform(0.6,0.8),2)  #鈍化状態
        self.driver_reaction_time      = self.driver_reaction_time_init #インスタンス生成時には初期値を設定
        #安全車頭時間T
        self.safety_head_time = 1.0
        #停止時最低車間距離
        self.stopping_min_car_distance = 1.65
        #希望速度
        #各車線の希望速度-10～0km/hで各車両の希望速度を散らす。これで車群が生まれやすくなる。
        vel_tmp = round(random.uniform(0,10),2)
        self.vel_hope = list(map(lambda x: (x - vel_tmp)/3.6, vel_hope))
        #初期速度
        v_clbr = 0 / 3.6
        self.vel_init = self.vel_hope[lane] + v_clbr 
        #高速道路時車線変更するか否か
        self.is_aggressive_driver = generate_random(10)

        #時間経過で毎回値が変わるパラメータ
        #前方位置
        self.front = 5
        #後方位置
        self.back  = 0
        #道路番号
        self.road_id = road_id
        #車線
        self.lane = lane
        #車両速度
        self.vel = self.vel_init
        #加速度
        self.accl = 0
        #車間距離
        self.inter_vehicle_distance = inter_vehicle_distance
        #前方車両との相対速度
        self.delta_vel = 0
        #前方車両ID
        self.front_car_id = front_car_id
        #前方車両インスタンス
        self.front_car = None
        #車線変更途中か否か
        self.shift_lane = 0
        #車線変更先の車線
        self.shift_lane_to = 0
        #車線変更開始時間
        self.shift_begin = 0
        #車線変更先車間距離
        self.shift_distance_go = 0
        #車線変更先前方車両ID
        self.shift_front_car_id = -1
        #目標車両ID
        self.target_id = -1

        #type
        #サグ部で減速するかどうか設定する。ratio_typeで割合を指定する。
        tmp_rng = random.random()

        #0-300秒までType2車両を発生させる
        if (tmp_rng <= ratio_type[2] and
            time < 5000
            ):
            self.type = 2
            
            #サグ部でどの速度まで減速するかを記録
            self.sag_target_vel = None
            #サグ部減速が終わったか否かのフラグ
            self.decerated_sag = False
        elif tmp_rng <= ratio_type[1] + ratio_type[2]:
            self.type = 1
        else:
            self.type = 0

        #サグ部による減速でサグ部入り時からどこまで速度を下げるか
        self.gravity_vel = -15/3.6
        
        #ここから【山内卒研】【渡邊修論】#
        #迂回情報(旅行時間測定用)
        if road_id == 0:
            self.detour_info = "highway"
        elif road_id == 1:
            self.detour_info = "general"
        else:
            self.detour_info = "None"

        #渋滞予見フラグ(ログ出力の関係で設定)
        self.jam_prevision_flag = None

        #渋滞吸収運転フラグ(ログ出力の関係で設定)
        self.jam_absorption_flag = None
        
        #ここからtype0限定処理
        if self.type != 0:
            return
        #最寄りIC
        self.nearest_ic = None
        #渋滞予見速度閾値
        self.jam_prevision_vel = jam_prevision_vel/3.6
        #渋滞予見フラグ
        self.jam_prevision_flag = 0
        
        #ここから【渡邊修論】#
        #渋滞予見フラグを下げる時間
        self.jam_prevision_time = 0

        #渋滞予見フラグ継続時間
        self.flag_continue_time = 100

        #渋滞吸収運転をしているかどうかのフラグ
        self.jam_absorption_flag = 0

        #渋滞吸収運転フラグを下げる時間
        self.jam_absorption_time = 0

        #渋滞吸収運転時の加速度
        self.jam_absorption_accl = -0.4

        #渋滞吸収運転を行う速度閾値
        self.jam_absorption_vel = 60/3.6

        #過去10秒間の速度記録用のリスト
        self.vel_record_tmp = MovingAverage(10*10)

    def cal_vel(self):
        '''
        加速度を加算して速度を更新
        '''
        self.vel += self.accl/10
        self.vel = round(self.vel,2)

        if self.vel < 0:
            self.vel = 0

    def cal_pos(self):
        '''
        速度を加算して現在位置を更新
        '''
        self.front=round(self.front+self.vel/10,2)#前方位置代入
        self.back =round(self.back +self.vel/10,2)#後方位置代入

    def update_dull_state(self):
        '''
        渋滞に巻き込まれたら一般車両(Type2車両)のみ鈍化
        鈍化は反応時間を増加させることによって再現
        '''

        #渋滞に巻き込まれた時に鈍化
        if (self.vel <= 40/3.6 and
            self.type != 0
        ):
            self.driver_reaction_time = self.driver_reaction_time_dull
        else:
            self.driver_reaction_time = self.driver_reaction_time_init

    def update_nearest_ic(self,road):
        '''
        【山内卒研】
        type0車両は最寄りICを更新
        '''
        if self.type != 0:
            return

        for ic_i, ic_pos in enumerate(road.ic_pos):
            if self.front > ic_pos:
                continue
            if ic_i == 0:
                self.nearest_ic = 0
                return
            if self.front > road.ic_pos[ic_i-1]:
                self.nearest_ic = ic_i
                return
        return None

    def jam_prevision(self):
        '''
        【山内卒研】
        type0車両が渋滞予見速度閾値を下回ったら、渋滞予見フラグを立てる
        '''
        if self.type != 0:
            return

        self.vel_record_tmp.put(self.vel)
        if self.vel_record_tmp.average() < self.jam_prevision_vel:
            self.jam_prevision_flag = 1
        else:
            self.jam_prevision_flag = 0

    def change_lane(self,road,dst_lane_i,time):
        '''
        車線変更可能かどうかを判定し、可能な場合確率で車線変更を実施
        '''

        #車線変更先が0または存在しない車線の場合車線変更をしない
        if dst_lane_i == 0 or dst_lane_i < 0 or dst_lane_i >= len(road.lane_lists):
            return

        #車線変更中車両
        if self.shift_lane==1:
            #車線変更開始から4秒経っていたら車線変更完了
            if time==self.shift_begin+40:
                self.lane=self.shift_lane_to
                self.shift_lane_to,self.shift_lane,self.shift_begin=0,0,0
            
            return 

        #初期値設定
        Pa = None
        Dpap=float("infinity")
        #NOTE infにしないと隣車線に車がいない場合車線変更しなくなってしまう
        Vpa =float("infinity")

        Pb = None
        Dppb=float("infinity")
        Vpb =-float("infinity")

        #変更先車線の車をイテレートする
        for dst_lane_car in road.lane_lists[dst_lane_i]:

            car_distance_front = dst_lane_car.front - self.front#前方位置同士を引き算

            if car_distance_front >= 0 and car_distance_front < Dpap:#0以上の最小値を調べている 
                Pa = dst_lane_car
                Dpap = car_distance_front #車間距離更新

            car_distance_back = self.front - dst_lane_car.front#前方位置同士を引き算

            if car_distance_back >= 0 and car_distance_back < Dppb:#0以上の最小値を調べている
                Pb = dst_lane_car
                Dppb = car_distance_back #車間距離更新

        #DpapとDppbをそれぞれ正式な車間距離に計算し直す
        if Pa != None:
            Dpap = Pa.back - self.front
            Vpa = Pa.vel

        if Pb != None:
            Dppb = self.back - Pb.front
            Vpb = Pb.vel

        #車線変更可能 前方車間距離
        Pa_delta_vel = self.vel - Vpa
        can_lane_change_distance_front = self.desired_vehicle_distance(delta_v = Pa_delta_vel)

        #車線変更可能 後方車間距離
        if self.vel<Vpb:
            can_lane_change_distance_back = (Vpb-self.vel)*(Vpb-self.vel) / self.desired_Deceleration / 2 + self.stopping_min_car_distance
        else:
            can_lane_change_distance_back=0

        #車線変更条件を満たさない場合return
        if not ((self.vel<=1 or self.accl<=0) and 
                (self.vel*3.6/2 < Dpap and self.vel*3.6/2 < Dppb) and 
                (Vpa>self.vel) and 
                (can_lane_change_distance_back<Dppb) and
                (can_lane_change_distance_front<Dpap)
                ):
            return

        def driver_judge(time):
            '''
            アグレッシブドライバーであれば100%車線変更、そうでない場合は1→2で50%、2→1で10%で車線変更
            '''
            #乱数テーブルリセット。時間と乗算することで、各時間ごとに疑似的に乱数を再現
            random.seed(self.seed * self.car_id * time)

            tmp_rnd = random.random()
            if self.is_aggressive_driver == 1:
                return 1
            if (dst_lane_i == 2 and
                tmp_rnd < 0.5):
                return 1
            if (dst_lane_i == 1 and
                tmp_rnd < 0.1):
                return 1
        
        if driver_judge(time):
            self.shift_lane   =1#車線変更してる途中かどうか
            self.shift_lane_to=dst_lane_i#どこの車線に変更しようとしてるか
            self.shift_begin  =time#車線変更開始時間
            
    def change_detour(self,detour_road,time):
        '''
        【渡邊修論】
        迂回可能かどうかを判定し、可能な場合迂回(もう一つの道路に車両を移動)を実施
        迂回先はlane:0で、迂回先の走行車線への合流はmerge_detourメソッドで行う
        '''
        # #追い越し車線を走っている場合はリターン
        # if self.lane == 2:
        #     return

        #初期値設定
        #迂回先のどの車線に移動させるか
        dst_lane = 0

        Pa = None
        Dpap=float("infinity")
        #NOTE infにしないと隣車線に車がいない場合車線変更しなくなってしまう
        Vpa =float("infinity")

        Pb = None
        Dppb=float("infinity")
        Vpb =-float("infinity")

        #変更先車線の車をイテレートする
        for dst_lane_car in detour_road.lane_lists[dst_lane]:

            car_distance_front = dst_lane_car.front - self.front#前方位置同士を引き算

            if car_distance_front >= 0 and car_distance_front < Dpap:#0以上の最小値を調べている 
                Pa = dst_lane_car
                Dpap = car_distance_front #車間距離更新

            car_distance_back = self.front - dst_lane_car.front#前方位置同士を引き算

            if car_distance_back >= 0 and car_distance_back < Dppb:#0以上の最小値を調べている
                Pb = dst_lane_car
                Dppb = car_distance_back #車間距離更新

        #DpapとDppbをそれぞれ正式な車間距離に計算し直す
        if Pa != None:
            Dpap = Pa.back - self.front
            Vpa = Pa.vel

        if Pb != None:
            Dppb = self.back - Pb.front
            Vpb = Pb.vel

        #車線変更可能 前方車間距離(澁谷さんのプログラム)
        Pa_delta_vel = self.vel - Vpa
        can_lane_change_distance_front = self.desired_vehicle_distance(delta_v = Pa_delta_vel)

        #車線変更可能 後方車間距離
        if self.vel<Vpb:
            can_lane_change_distance_back = (Vpb-self.vel)*(Vpb-self.vel) / self.desired_Deceleration / 2 + self.stopping_min_car_distance
        else:
            can_lane_change_distance_back=0

        #車線変更条件を満たさない場合return
        #加速度・速度条件以外はchange_laneと同じ。速度や加速度は一般道と高速道路で明らかに違うため除外
        if not (#(self.vel*3.6/2 < Dpap and self.vel*3.6/2 < Dppb) and 
                (can_lane_change_distance_back<Dppb) and
                (can_lane_change_distance_front<Dpap)
                ):
            return False

        #道路変更に伴う更新
        #TODO 設定箇所が分散するので、最終的にはどこかしらにひとまとめにした方がいいかもしれない

        #乱数テーブルリセット
        random.seed(self.seed * self.car_id * time)

        #希望速度
        #各車両の希望速度-10～0km/hで各車両の希望速度を散らす。これで車群が生まれやすくなる。
        vel_tmp = round(random.uniform(0,10),2)
        self.vel_hope = list(map(lambda x: (x - vel_tmp)/3.6, detour_road.vel_hope_max))
        #迂回用レーンの希望速度を強制的に迂回先の走行車線速度-15km/hに設定
        self.vel_hope[0] = (detour_road.vel_hope_max[1] - 15)/3.6
        #道路番号
        self.road_id = detour_road.id
        #車線
        self.lane = dst_lane

        #最寄りIC(一般道にICはないという設定)
        self.nearest_ic = None

        #迂回情報(旅行時間測定用)
        self.detour_info = "pre-detour"

        return True

    def merge_detour(self,detour_road,time):
        '''
        【渡邊修論】
        迂回した車両を迂回レーン(lane:0)から迂回道路の走行車線に車線変更する
        '''
        #車線変更中車両
        if self.shift_lane == 1:
            #車線変更開始から2秒経っていたら車線変更完了
            if time == self.shift_begin + 20:
                self.lane = self.shift_lane_to
                self.shift_lane_to,self.shift_lane,self.shift_begin = 0,0,0
                
                #迂回情報(旅行時間測定用)
                self.detour_info = "detour"
            
            return

        #初期値設定
        #迂回先のどの車線に移動させるか
        dst_lane = 1

        Pa = None
        Dpap=float("infinity")
        #NOTE infにしないと隣車線に車がいない場合車線変更しなくなってしまう
        Vpa =float("infinity")

        Pb = None
        Dppb=float("infinity")
        Vpb =-float("infinity")

        #変更先車線の車をイテレートする
        for dst_lane_car in detour_road.lane_lists[dst_lane]:

            car_distance_front = dst_lane_car.front - self.front#前方位置同士を引き算

            if car_distance_front >= 0 and car_distance_front < Dpap:#0以上の最小値を調べている 
                Pa = dst_lane_car
                Dpap = car_distance_front #車間距離更新

            car_distance_back = self.front - dst_lane_car.front#前方位置同士を引き算

            if car_distance_back >= 0 and car_distance_back < Dppb:#0以上の最小値を調べている
                Pb = dst_lane_car
                Dppb = car_distance_back #車間距離更新

        #DpapとDppbをそれぞれ正式な車間距離に計算し直す
        if Pa != None:
            Dpap = Pa.back - self.front
            Vpa = Pa.vel

        if Pb != None:
            Dppb = self.back - Pb.front
            Vpb = Pb.vel

        #車線変更可能 前方車間距離(澁谷さんのプログラム)
        Pa_delta_vel = self.vel - Vpa
        can_lane_change_distance_front = self.desired_vehicle_distance(delta_v = Pa_delta_vel)

        #車線変更可能 後方車間距離
        if self.vel<Vpb:
            can_lane_change_distance_back = (Vpb-self.vel)*(Vpb-self.vel) / self.desired_Deceleration / 2 + self.stopping_min_car_distance
        else:
            can_lane_change_distance_back=0

        #車線変更条件を満たさない場合return
        #後ろの車両と衝突しなければ合流
        if not (#(self.vel*3.6/2 < Dpap and self.vel*3.6/2 < Dppb) and 
                (can_lane_change_distance_back<Dppb) and
                (can_lane_change_distance_front<Dpap)
                ):
            return

        self.shift_lane    = 1#車線変更してる途中かどうか
        self.shift_lane_to = dst_lane#どこの車線に変更しようとしてるか
        self.shift_begin   = time#車線変更開始時間

    def relative_front_car(self,lane_lists):
        '''
        前を走行する車両を調べて、車間距離や相対速度を計算し、更新
        '''

        lane_i = self.lane
        run_car_i_lane = lane_lists[lane_i].index(self)
    
        if run_car_i_lane == 0 :#前に車がいないとき
            front_car_id = -1
            delta_v = 0
            car_distance = float("infinity")
        else:
            self.front_car = lane_lists[lane_i][run_car_i_lane-1]
            car_distance = self.front_car.back-self.front
            #delta_vを調べる処理,delta_vは前の車両との速度差
            delta_v = self.vel - self.front_car.vel#自分の速度－相手の速度
            front_car_id = self.front_car.car_id

        self.front_car_id = front_car_id
        self.inter_vehicle_distance = round(car_distance,2)#車間距離代入
        self.delta_vel = round(delta_v,2)#相対速度

    def desired_vehicle_distance(self,
                                 delta_v = None):
        '''
        IDMより希望車間距離s*を計算
        '''

        s0= self.stopping_min_car_distance
        v = self.vel
        T = self.safety_head_time
        Treac   = self.driver_reaction_time
        a = self.max_accl
        b = self.desired_Deceleration

        #引数に相対速度が渡されなかった場合はインスタンスが持っている相対速度(前の車との相対速度)を使う
        if delta_v is None:
            delta_v = self.delta_vel

        ss = round(s0+v*(T+Treac)+((v*delta_v)/(((a*b)**0.5)*2)),1)

        #希望車間距離が停止時最低車間距離より小さい場合は停止時最低車間距離に置き変える
        if ss < s0:
            ss = s0

        return ss

    def IDM_car_accl(self,run_car_list):
        '''
        cal_acclのサポートメソッド
        IDM+から加速度を計算
        車線変更時は車線変更先を考慮した加速度を計算
        '''
        def cal_accl_idm(ss):
            a = self.max_accl
            v = self.vel
            s = self.inter_vehicle_distance
            vd= self.vel_hope[self.lane]

            #0除算対策
            if s <= 0:
                s = 0.1

            accl=round(a*min(1-(v/vd)**4,1-(ss/s)**2,key=int),1)
            
            if accl < -3.8:#-self.desired_Deceleration:
                accl = -3.8

            return accl

        #★以下は通常の車両追従の加速度算出
        #IDM+の式を使って希望車間距離を調べる処理
        desired_vehicle_distance = self.desired_vehicle_distance()

        #IDM+の式を使って希望車間距離から加速度算出
        car_accl = cal_accl_idm(desired_vehicle_distance)

        #target_idはどの車両を目指して走行するかを示す。
        target_id = self.front_car_id

        #★以下は車線変更の途中を考慮した加速度算出
        #〇前方で車線変更している車がいたらそれに合わせる
        #shift_distance_comeは車線変更しようとしてくる車両との車間距離
        shift_distance_come = float("infinity")
        #shift_id_comeは前方で車線変更する車両ID,いない場合は-1
        shift_id_come = -1
        desired_vehicle_distance_come = 0
        for i in run_car_list:
            #車線変更しようとしてる,自分のいる車線に変更しようとしてる
            if i.shift_lane == 1 and i.shift_lane_to == self.lane:
                shift_distance_come_tmp = i.front-self.front
                if 0<shift_distance_come_tmp < shift_distance_come:#0以上の最小値を調べている
                    shift_distance_come = shift_distance_come_tmp #車間距離更新
                    shift_id_come = i
    
        if shift_id_come !=-1:
            #車線変更しようとしている車両との車間距離
            shift_distance_come = shift_id_come.back - self.front
            #車線変更しようとしている車両との相対速度
            shift_delta_v_come  = self.vel - shift_id_come.vel

            #希望車間距離を調べる処理
            self.delta_vel = shift_delta_v_come
            desired_vehicle_distance_come = self.desired_vehicle_distance()
            if shift_distance_come < 0:
                #-0.5の根拠が分からない by山内
                car_accl_come = -0.5
            else:
                #希望車間距離から加速度算出
                self.inter_vehicle_distance = shift_distance_come
                car_accl_come = cal_accl_idm(desired_vehicle_distance_come)
            if car_accl_come < car_accl:
                car_accl  = car_accl_come
                target_id = shift_id_come.car_id

        #〇自分が車線変更しようとしてるならば、車線変更先の前方車両に速度をあわせる
        #車線変更先の前方車両との車間距離
        shift_distance_go = float("infinity")
        #車間距離先の前方車両ID
        shift_id_go = -1
        #車線変更先の前方車両との希望車間距離
        desired_vehicle_distance_go = 0
        if self.shift_lane == 1:#自分が車線変更しているとき
            for i in run_car_list:#車線変更先の前方車両を探す
                if i.lane == self.shift_lane_to:#探している車が車線変更先と同じ車線のとき
                    shift_distance_go_tmp = i.front - self.front
                    if shift_distance_go_tmp > 0 and shift_distance_go_tmp < shift_distance_go:#0以上の最小値を調べている
                        shift_distance_go = shift_distance_go_tmp #車間距離更新
                        shift_id_go = i
        
            if shift_id_go !=-1:#車線変更先の前方車両がいたら
                #車線変更先の前方車両の後方位置-自分の前方位置
                shift_distance_go = shift_id_go.back - self.front
                #相対速度
                shift_delta_v_go  = self.vel - shift_id_go.vel
            
                #希望車間距離を調べる処理
                self.delta_vel = shift_delta_v_go
                desired_vehicle_distance_go = self.desired_vehicle_distance()
            if shift_distance_go < 0:
                car_accl_go = -0.5
            else:
                self.inter_vehicle_distance = shift_distance_go
                car_accl_go = cal_accl_idm(desired_vehicle_distance_go)

            if car_accl_go < car_accl:
                car_accl  = car_accl_go
                target_id = shift_id_go.car_id

        #以下はログデータに9999や0が続いていると見にくいから消す処理
        if shift_distance_go == float("infinity") or shift_distance_go==0:
            shift_distance_go = None
        #ここまで加速度処理

        #オブジェクトだった場合数字に置き換える(これはオブジェクトに変えた余波なので、あとでうまいこと直したほうが良い)
        if shift_id_go != -1:
            shift_id_go = shift_id_go.car_id

        self.shift_distance_go  = shift_distance_go#車線変更先車間距離
        self.shift_front_car_id = shift_id_go      #車線変更先前方車両ID
        self.target_id = target_id                #目標車両ID

        #加速度代入
        self.accl = car_accl

    def sag_car_accl(self,sag):
        '''
        cal_acclのサポートメソッド
        type2車両がサグ部に入った場合、サグ部を考慮した加速度を計算
        '''
        
        #type2車両がサグ部に入ったとき減速、そうでないときは通常通り加速
        if (self.back >= sag["start"] and self.front <= sag["end"] and
            self.type == 2 and
            self.decerated_sag == False
            ):

            #サグ部入り時の速度から減速目標速度を記録
            if self.sag_target_vel == None:
                self.sag_target_vel = self.vel + self.gravity_vel
                #サグ部減速下限設定(とりあえず10km/h)
                if self.sag_target_vel < 15/3.6:
                    self.sag_target_vel = 15/3.6

            #減速目標速度まで減速
            if self.accl <= 0:
                self.accl = self.accl + sag["gravity_accl"]
            else:
                self.accl = sag["gravity_accl"]

            #減速が終わったらフラグを立ててもう一回減速しないようにする
            if self.vel < self.sag_target_vel:
                self.decerated_sag = True

    def jad_car_accl(self):
        '''
        cal_acclのサポートメソッド
        type0車両が渋滞吸収運転している場合、渋滞吸収運転を考慮した加速度を計算
        '''
        if self.type == 0:

            if (self.jam_absorption_flag == 1 and 
                self.vel > self.jam_absorption_vel
                ):
                
                if self.accl <= 0:
                    self.accl = self.accl + self.jam_absorption_accl
                else:
                    self.accl = self.jam_absorption_accl

    def cal_accl(self,road):
        '''
        IDM+,サグ部等を考慮した加速度を計算し、更新
        '''
        #IDM+を使った加速度計算
        self.IDM_car_accl(road.run_car_list)

        #サグ部を考慮した加速度計算
        self.sag_car_accl(road.sag)

        #渋滞吸収運転時の加速度計算
        self.jad_car_accl()

        #加速度代入
        self.accl = round(self.accl,2)             

    def log_out_obj(self,time):
        '''
        logで出力したいパラメータのみを集めたオブジェクトを作成して吐き出す
        '''
        logdict = dict(time    = time,
                       car_id  = self.car_id,
                       front   = self.front,
                       back    = self.back,
                       road_id = self.road_id,
                       lane    = self.lane,
                       vel     = round(self.vel,2),
                       accl    = round(self.accl,2),
                       inter_vehicle_distance = round(self.inter_vehicle_distance,2),
                       delta_vel     = round(self.delta_vel,2),
                       front_car_id  = self.front_car_id,
                       shift_lane    = self.shift_lane,
                       shift_lane_to = self.shift_lane_to,
                       shift_begin   = self.shift_begin,
                       shift_distance_go  = self.shift_distance_go,
                       shift_front_car_id = self.shift_front_car_id,
                       target_id = self.target_id,
                       type = self.type,
                       jam_prevision_flag = self.jam_prevision_flag,
                       jam_absorption_flag = self.jam_absorption_flag,
                       detour_info = self.detour_info)

        return SimpleNamespace(**logdict)