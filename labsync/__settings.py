#datamanager(s) get(s) mailed in case of errors
DM = ['justin.time@uu.nl', 'w.i.l.debras@uu.nl'] #for each recient, a new mail

#dict to check file specifications and numbers (sense)
CHECK_D = {
        'chantigap':('*settings.txt', '*all_gazedata.mat', '*all_gazedata.csv', 
                    '*all_trials.csv', '*all_trials.mat', '*calib_*.mat', 
                    '*conditions.mat', '*report.zip', '*backup.zip'),
        'chprogap': ('*settings.txt', '*all_gazedata.mat', '*all_gazedata.csv', 
                    '*all_trials.csv', '*all_trials.mat', '*calib_*.mat', 
                    '*conditions.mat', '*report.zip', '*backup.zip'),
        'chsgaze':  ('*settings.txt', '*all_gazedata.mat', '*all_gazedata.csv', 
                    '*all_trials.csv', '*all_trials.mat', '*calib_*.mat', 
                    '*report.zip', '*backup.zip' ),
        'cyberball':('*settings.txt','*.csv', '*.mat'),
        'discount': ('*settings.txt', '*.txt'),
        'peabody':  ('*settings.txt', '*.csv', '*.mat', '*answers.csv'),
        'trustgame':('*settings.txt', '*.csv', '*.mat'),
        'infprogap':('*settings.txt', '*all_gazedata.mat', '*all_gazedata.csv', 
                    '*all_trials.csv', '*all_trials.mat', '*calib_*.mat', 
                    '*conditions.mat', '*report.zip', '*backup.zip'),
        'infpop': ('*settings.txt', '*all_gazedata.mat', '*all_gazedata.csv', 
                    '*all_trials.csv', '*all_trials.mat', '*calib_*.mat', 
                    '*report.zip', '*backup.zip'),
        'infsgaze': ('*settings.txt', '*all_gazedata.mat', '*all_gazedata.csv', 
                    '*all_trials.csv', '*all_trials.mat', '*calib_*.mat', 
                    '*report.zip', '*backup.zip'),
        'coherence':('*settings.txt', '*.mat', '*.mp4', '*.bdf'),
        'faceemo':  ('*settings.txt', '*.mat', '*.csv', '*.mp4', '*.bdf'),
        'facehouse':('*settings.txt', '*.mat', '*.csv', '*.mp4', '*.bdf')
        }
        
#dict to generate random bytes datasets/files for varying types
CREATE_D = {
        'chantigap':{'settings.txt':291, 'all_gazedata.mat':430991, 
                    'all_gazedata.csv':4468509,'all_trials.csv':2945, 
                    'all_trials.mat':2390, 'calib_1.mat':1213, 
                    'conditions.mat':652, 'report.zip':166088, 
                    'backup.zip':6575729},
        'chprogap': {'settings.txt':291, 'all_gazedata.mat':450991, 
                    'all_gazedata.csv':4868509, 'all_trials.csv':3062,
                    'all_trials.mat': 2503, 'calib_1.mat':1291, 
                    'conditions.mat':734, 'report.zip':177097, 
                    'backup.zip':8575729},
        'chsgaze':{'settings.txt':291, 'all_gazedata.mat':450991, 
                    'all_gazedata.csv':4868509, 'all_trials.csv':3062,
                    'all_trials.mat': 2503, 'calib_1.mat':1291, 
                    'report.zip':177097, 'backup.zip':8575729},
        'cyberball':{'settings.txt':269, '.csv':1581, '.mat':329968},
        'discount': {'settings.txt':238, '.txt':10666 },
        'peabody':  {'settings.txt':291, '.csv':10777, '.mat':32881, 
                    'answers.csv':7800},
        'trustgame':{'settings.txt':286, '.csv':9700, '.mat':4500},
        'infprogap':{'settings.txt':291, 'all_gazedata.mat':830991, 
                    'all_gazedata.csv':6468509, 'all_trials.csv':2700, 
                    'all_trials.mat':1850, 'calib_1.mat':1500, 
                    'conditions.mat':700, 'report.zip':267098, 
                    'backup.zip':9575729},
        'infpop': {'settings.txt':291, 'all_gazedata.mat':931085, 
                    'all_gazedata.csv':5868509, 'all_trials.csv':2680, 
                    'all_trials.mat':1960, 'calib_1.mat':1377 , 
                    'report.zip':217097, 'backup.zip':10575729},
        'infsgaze': {'settings.txt':298, 'all_gazedata.mat':830991, 
                    'all_gazedata.csv':1830991, 'all_trials.csv':2100, 
                    'all_trials.mat':1556, 'calib_1.mat':1384, 
                    'report.zip':177087, 'backup.zip':10575745},
        'coherence':{'settings.txt':256, '.mat':6280, '.mp4':22963111, 
                    '.bdf':112611840},
        'faceemo':  {'settings.txt':256 , '.mat':11136, '.csv':943, 
                    '.mp4':23821322, '.bdf':68276736},
        'facehouse':{'settings.txt':256 , '.mat':11136, '.csv':943, 
                    '.mp4':23821322, '.bdf':68276736},
        }

WAVE_D = {
        'chantigap': ['9y','12y','15y'],
        'chprogap':['9y','12y','15y'],
        'chsgaze':['9y','12y','15y'],
        'cyberball':['9y','12y','15y'],
        'discount':['9y','12y','15y'],
        'peabody':['9y','12y','15y'],
        'trustgame':['9y','12y','15y'],
        'infprogap':['5m', '10m'],
        'infsgaze':['5m', '10m'],
        'infpop':['5m','10m'],
        'coherence':['5m', '10m'],
        'faceemo':['10m'],
        'facehouse':['5m','10m']
        }
        
PSEUDO_D = {
        'chantigap': 'A',
        'chprogap':'A',
        'chsgaze':'A',
        'cyberball':'A',
        'discount':'A',
        'peabody':'A',
        'trustgame':'A',
        'infprogap':'B',
        'infsgaze':'B',
        'infpop':'B',
        'coherence':'B',
        'faceemo':'B',
        'facehouse':'B'
        }

ID_D = {
    'Gander':'DELL1',
    'Donald':'DELL2',
    'Dagobert':'DELL3',
    'Quack':'DELL4',
    'Mickey':'MAC1',
    'Minnie':'MAC2',
    'Goofy':'MAC3',
    }
    
#testlist for checking file specs with three too long pseudo's and two wrong dates 
TEST_LIST = ['A02980_9y_trustgame_20160706_1432_MAC04',
    'A02980_9y_trustgame_20160706_1432_settings.txt',
    'A02980_9y_trustgame_20160706_1432.csv',
    'A02980_9y_trustgame_20160706_1432.mat',
    'A08024_9y_cyberball_20160633_1550_MAC04', #
    'A08024_9y_cyberball_20160622_1550_settings.txt',
    'A08024_9y_cyberball_20160622_1550.csv',
    'A080246_9y_cyberball_20160622_1550.mat',#
    'A08024_9y_discount_20160622_1545_MAC04',
    'A08024_9y_discount_20160622_1545_settings.txt',
    'A08024_9y_discount_20160622_1545.txt',
    'A58094_9y_cyberball_20160624_1516_MAC04',
    'A580947_9y_cyberball_20160624_1516_settings.txt',#
    'A58094_9y_cyberball_20160624_1516.csv',
    'A58094_9y_cyberball_20161324_1516.mat',#
    'A58094_9y_discount_20160624_1514_MAC04',
    'A58094_9y_peabody_20160624_1501_MAC04',
    'A58094_9y_peabody_20160624_1501_answers.csv',
    'A580946_9y_peabody_20160624_1501_settings.txt',#
    'A58094_9y_peabody_20160624_1501.csv',
    'A58094_9y_peabody_20160624_1501.mat',
    'A70886_9y_cyberball_20160602_1602_MAC04',
    'A87171_9y_discount_20160603_1547_settings.txt']
