import pandas as pd
import requests
import io
import yfinance as yf


# Download SIX ticker list
def get_six_tickers():
    url = 'https://www.six-group.com/sheldon/equity_issuers/v1/equity_issuers.csv'
    response = requests.get(url, verify=False)
    df = pd.read_csv(io.StringIO(response.text), on_bad_lines='skip', header=0, sep=';')
    tickers = df['Symbol'].tolist()
    tickers = [t.replace('.', '-') for t in tickers]  # Convert for yfinance
    return tickers


# Download S&P 500 ticker list
def get_sp500_tickers_wikipedia():
	url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
	tables = pd.read_html(url)
	tickers = tables[0]['Symbol'].tolist()
	tickers = [t.replace('.', '-') for t in tickers] # Convert for yfinance    
	return tickers


# S&P400 midcap with pandas_datareader and Wikipedia
def get_sp_midcap_wikipedia():
    """
    Get the list of tickers S&P MidCap 400 from Wikipedia
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
    
    tables = pd.read_html(url)
    tickers = tables[0]['Symbol'].tolist()
    tickers = [t.replace('.', '-') for t in tickers] # Convert for yfinance    
    return tickers

# S&P400 midcap with yfinance
def get_sp_midcap_yfinance():
    """
    Get theS&P MidCap 400 tickers using yfinance
    """
    ticker = "^SP400"
    sp_midcap = yf.Ticker(ticker)
    
    try:
        # Попытка получить компоненты индекса
        components = sp_midcap.components
        return list(components.index)
    except:
        print("Could not get components from yfinance.")
        return []

def get_all_us_tickers():
    arr = [
        'A','AA','AAL','AAOI','AAON','AAP','AAPL','AAT','ABBV','ABCB','ABG','ABM','ABNB','ABR','ABSI','ABT','ABUS','ACA','ACAD','ACCD','ACCO','ACEL','ACGL','ACHC','ACHR','ACI','ACIW','ACLS','ACLX','ACM','ACMR','ACN','ACRE','ACT','ACVA','ADBE','ADC','ADEA','ADI','ADM','ADMA','ADNT','ADP','ADPT','ADRO','ADSK','ADT','ADTN','ADUS','ADVM','AEE','AEHR','AEIS','AEO','AEP','AES','AESI','AFG','AFL','AFRM','AGCO','AGEN','AGIO','AGL','AGM','AGNC','AGO','AGR','AGS','AGX','AGYS','AHCO','AHH','AHR','AI','AIG','AIN','AIOT','AIR','AIT','AIV','AIZ','AJG','AKAM','AKBA','AKR','AKRO','AL','ALAB','ALB','ALCO','ALDX','ALE','ALEC','ALEX','ALG','ALGM','ALGN','ALGT','ALHC','ALIT','ALK','ALKS','ALKT','ALL','ALLE','ALLO','ALLY','ALNT','ALNY','ALRM','ALRS','ALSN','ALT','ALTG','ALTM','ALTR','ALV','ALX','ALXO','AM','AMAL','AMAT','AMBA','AMBC','AMC','AMCR','AMD','AME','AMED','AMG','AMGN','AMH','AMKR','AMN','AMP','AMPH','AMPL','AMPS','AMR','AMRC','AMRK','AMRX','AMSC','AMSF','AMT','AMTB','AMTM','AMWD','AMWL','AMZN','AN','ANAB','ANDE','ANET','ANF','ANGO','ANIK','ANIP','ANNX','ANSS','AON','AORT','AOS','AOSL','APA','APAM','APD','APEI','APG','APGE','APH','APLD','APLE','APLS','APLT','APO','APOG','APP','APPF','APPN','APTV','AR','ARCB','ARCH','ARCT','ARDX','ARE','ARES','ARHS','ARI','ARIS','ARKO','ARLO','ARMK','AROC','AROW','ARQT','ARR','ARRY','ARTNA','ARVN','ARW','ARWR','ASAN','ASB','ASGN','ASH','ASIX','ASO','ASPN','ASRT','ASTE','ASTH','ASTS','ATEC','ATEN','ATEX','ATGE','ATI','ATKR','ATMU','ATNI','ATO','ATR','ATRC','ATRO','ATSG','ATUS','ATXS','AUB','AUR','AURA','AVA','AVAV','AVB','AVBP','AVD','AVDX','AVGO','AVIR','AVNS','AVNT','AVNW','AVO','AVPT','AVT','AVTR','AVXL','AVY','AWI','AWK','AWR','AX','AXGN','AXL','AXNX','AXON','AXP','AXS','AXSM','AXTA','AYI','AZEK','AZO','AZPN','AZTA','AZZ',
        'B','BA','BAC','BAH','BALL','BANC','BAND','BANF','BANR','BASE','BATRA','BATRK','BAX','BBIO','BBSI','BBW','BBWI','BBY','BC','BCC','BCML','BCO','BCPC','BCRX','BDC','BDN','BDX','BE','BEAM','BECN','BELFB','BEN','BERY','BFA','BFAM','BFB','BFC','BFH','BFS','BFST','BG','BGC','BGS','BHB','BHE','BHF','BHLB','BHRB','BHVN','BIGC','BIIB','BILL','BIO','BJ','BJRI','BK','BKD','BKE','BKH','BKNG','BKR','BKU','BL','BLBD','BLD','BLDR','BLFS','BLK','BLKB','BLMN','BLND','BLNK','BLUE','BLZE','BMBL','BMI','BMRC','BMRN','BMY','BNED','BNL','BOC','BOH','BOKF','BOOM','BOOT','BOWL','BOX','BPMC','BPOP','BPRN','BR','BRBR','BRC','BRDG','BRKB','BRKL','BRKR','BRO','BROS','BRSP','BRX','BRY','BRZE','BSIG','BSX','BSY','BTSG','BTU','BURL','BUSE','BV','BWA','BWB','BWIN','BWXT','BX','BXC','BXMT','BXP','BY','BYD','BYND','BYON','BZH',
        'C','CABA','CABO','CAC','CACC','CACI','CADE','CAG','CAH','CAKE','CAL','CALM','CALX','CAR','CARE','CARG','CARR','CARS','CART','CASH','CASS','CASY','CAT','CATX','CATY','CAVA','CB','CBAN','CBFV','CBL','CBOE','CBRE','CBRL','CBSH','CBT','CBU','CBZ','CC','CCB','CCBG','CCCC','CCCS','CCI','CCK','CCL','CCNE','CCO','CCOI','CCRN','CCS','CCSI','CDE','CDLX','CDMO','CDNA','CDNS','CDP','CDRE','CDW','CE','CECO','CEG','CEIX','CELC','CELH','CENTA','CENX','CERS','CERT','CEVA','CF','CFB','CFFN','CFG','CFLT','CFR','CG','CGEM','CGNX','CGON','CHCO','CHCT','CHD','CHDN','CHE','CHEF','CHGG','CHH','CHPT','CHRD','CHRS','CHRW','CHTR','CHUY','CHWY','CHX','CI','CIEN','CIFR','CIM','CINF','CIVI','CL','CLB','CLBK','CLDT','CLDX','CLF','CLFD','CLH','CLMT','CLNE','CLOV','CLSK','CLVT','CLW','CLX','CMA','CMC','CMCO','CMCSA','CME','CMG','CMI','CMP','CMPR','CMS','CMTG','CNA','CNC','CNDT','CNH','CNK','CNM','CNMD','CNNE','CNO','CNOB','CNP','CNS','CNX','CNXC','CNXN','COCO','COF','COGT','COHR','COHU','COIN','COKE','COLB','COLD','COLL','COLM','COMM','COMP','COO','COOP','COP','COR','CORT','CORZ','COST','COTY','COUR','CPAY','CPB','CPK','CPRI','CPRT','CPRX','CPT','CR','CRAI','CRBP','CRBU','CRC','CRCT','CRDO','CRGX','CRGY','CRH','CRI','CRK','CRL','CRM','CRMT','CRNC','CRNX','CROX','CRS','CRSP','CRSR','CRUS','CRVL','CRWD','CSCO','CSGP','CSGS','CSL','CSR','CSTL','CSV','CSWI','CSX','CTAS','CTBI','CTKB','CTLP','CTLT','CTO','CTOS','CTRA','CTRE','CTRI','CTS','CTSH','CTVA','CUBE','CUBI','CUR','CURB','CUZ','CVBF','CVCO','CVGW','CVI','CVLG','CVLT','CVNA','CVS','CVX','CW','CWAN','CWCO','CWEN','CWENA','CWH','CWK','CWST','CWT','CXM','CXT','CXW','CYH','CYRX','CYTK','CZR',
        'D','DAKT','DAL','DAN','DAR','DASH','DAWN','DAY','DBD','DBI','DBRG','DBX','DCI','DCO','DCOM','DD','DDD','DDOG','DDS','DE','DEA','DECK','DEI','DELL','DENN','DFH','DFIN','DFS','DG','DGICA','DGII','DGX','DH','DHC','DHI','DHIL','DHR','DIN','DINO','DIOD','DIS','DJCO','DJT','DK','DKNG','DKS','DLB','DLR','DLTR','DLX','DM','DMRC','DNA','DNB','DNLI','DNOW','DNTH','DNUT','DOC','DOCN','DOCS','DOCU','DORM','DOV','DOW','DPZ','DRH','DRI','DRS','DRVN','DSGR','DT','DTE','DTM','DUK','DUOL','DV','DVA','DVAX','DVN','DX','DXC','DXCM','DXPE','DY','DYN',
        'EA','EAF','EAT','EB','EBAY','EBC','EBF','EBMT','EBS','ECL','ECPG','ECVT','ED','EDIT','EDR','EE','EEFT','EFC','EFSC','EFX','EG','EGBN','EGHT','EGP','EGY','EHAB','EHC','EIG','EIX','EL','ELAN','ELF','ELME','ELS','ELV','ELVN','EMBC','EME','EMN','EMR','ENOV','ENPH','ENR','ENS','ENSG','ENTA','ENTG','ENV','ENVA','ENVX','EOG','EOLS','EOSE','EPAC','EPAM','EPC','EPR','EPRT','EQBK','EQC','EQH','EQIX','EQR','EQT','ERAS','ERIE','ERII','ES','ESAB','ESE','ESGR','ESI','ESNT','ESPR','ESQ','ESRT','ESS','ESTC','ESZ4','ETD','ETN','ETNB','ETR','ETSY','ETWO','EVBN','EVER','EVGO','EVH','EVLV','EVR','EVRG','EVRI','EVTC','EW','EWBC','EWCZ','EWTX','EXAS','EXC','EXE','EXEL','EXLS','EXP','EXPD','EXPE','EXPI','EXPO','EXR','EXTR','EYE','EYPT','EZPW',
        'F','FA','FAF','FANG','FAST','FATE','FAZ4','FBIN','FBK','FBMS','FBNC','FBP','FBRT','FC','FCBC','FCEL','FCF','FCFS','FCN','FCNCA','FCPT','FCX','FDMT','FDP','FDS','FDX','FE','FELE','FERG','FFBC','FFIC','FFIN','FFIV','FFWM','FG','FGF','FHB','FHI','FHN','FI','FIBK','FICO','FIGS','FIP','FIS','FITB','FIVE','FIVN','FIX','FIZZ','FL','FLEX','FLGT','FLIC','FLNC','FLO','FLR','FLS','FLUT','FLYW','FMBH','FMC','FMNB','FN','FNA','FNB','FND','FNF','FNKO','FOLD','FOR','FORM','FORR','FOUR','FOX','FOXA','FOXF','FPI','FR','FRAF','FRME','FRPH','FRPT','FRSH','FRT','FSFG','FSLR','FSLY','FSS','FTAI','FTDR','FTI','FTNT','FTRE','FTV','FUBO','FUL','FULC','FULT','FUN','FWONA','FWONK','FWRD','FWRG','FYBR',
        'G','GABC','GAP','GATO','GATX','GBCI','GBTG','GBX','GCI','GCMG','GCO','GD','GDDY','GDEN','GDOT','GDRX','GDYN','GE','GEF','GEFB','GEHC','GEN','GEO','GERN','GES','GEV','GEVO','GFF','GGG','GH','GHC','GIC','GIII','GILD','GIS','GKOS','GL','GLDD','GLPI','GLW','GM','GME','GMED','GMRE','GMS','GNE','GNK','GNL','GNRC','GNTX','GNW','GO','GOGO','GOLF','GOOD','GOOG','GOOGL','GPC','GPI','GPK','GPMT','GPN','GPOR','GPRE','GPRO','GRAL','GRBK','GRC','GRMN','GRPN','GS','GSAT','GSBC','GSHD','GT','GTES','GTLB','GTLS','GTN','GTX','GTXI','GTY','GVA','GWRE','GWW','GXO','GYRE',
        'H','HAE','HAIN','HAL','HALO','HAS','HASI','HAYN','HAYW','HBAN','HBI','HBNC','HCA','HCAT','HCC','HCI','HCKT','HCP','HCSG','HD','HDSN','HE','HEES','HEI','HEIA','HELE','HES','HFWA','HGV','HHH','HI','HIFS','HIG','HII','HIMS','HIW','HL','HLF','HLI','HLIO','HLIT','HLMN','HLNE','HLT','HLVX','HLX','HMN','HNI','HNR','HNST','HOG','HOLX','HOMB','HON','HONE','HOOD','HOPE','HOUS','HOV','HP','HPE','HPP','HPQ','HQY','HR','HRB','HRI','HRL','HRMY','HROW','HRTG','HRTX','HSIC','HSII','HST','HSTM','HSY','HTBI','HTBK','HTH','HTLD','HTLF','HTZ','HUBB','HUBG','HUBS','HUM','HUMA','HUN','HURN','HUT','HVT','HWC','HWKN','HWM','HXL','HY','HZO',
        'IAC','IART','IAS','IBCP','IBKR','IBM','IBOC','IBP','IBRX','IBTA','IBTX','ICE','ICFI','ICHR','ICUI','IDA','IDCC','IDT','IDXX','IDYA','IE','IESC','IEX','IFF','IIIN','IIIV','IIPR','ILMN','ILPT','IMKTA','IMMR','IMNM','IMVT','IMXI','INBX','INCY','INDB','INDI','INFA','INFN','INGR','INH','INN','INOD','INSM','INSP','INST','INSW','INTA','INTC','INTU','INVA','INVH','INVX','IONQ','IONS','IOSP','IOT','IOVA','IP','IPAR','IPG','IPGP','IQV','IR','IRBT','IRDM','IRM','IRON','IRT','IRTC','IRWD','ISRG','IT','ITCI','ITGR','ITOS','ITRI','ITT','ITW','IVR','IVT','IVZ',
        'J','JACK','JAMF','JANX','JAZZ','JBGS','JBHT','JBI','JBL','JBLU','JBSS','JBT','JCI','JCS','JEF','JELD','JHG','JJSF','JKHY','JLL','JMSB','JNJ','JNPR','JOBY','JOE','JOUT','JPM','JRVR','JWN','JXN',
        'K','KAI','KALU','KALV','KAR','KBH','KBR','KD','KDP','KE','KELYA','KEX','KEY','KEYS','KFRC','KFY','KGS','KHC','KIDS','KIM','KIND','KKR','KLAC','KLG','KLIC','KMB','KMI','KMPR','KMT','KMX','KN','KNF','KNSL','KNTK','KNX','KO','KODK','KOP','KOS','KR','KRC','KREF','KRG','KRNY','KROS','KRRO','KRUS','KRYS','KSS','KTB','KTOS','KURA','KVUE','KVYO','KW','KWR','KYMR',
        'L','LAB','LAD','LADR','LAMR','LANC','LAND','LASR','LAUR','LAZ','LAZR','LBPH','LBRDA','LBRDK','LBRT','LBTYA','LBTYK','LC','LCID','LCII','LDOS','LEA','LECO','LEG','LEN','LENB','LESL','LEU','LEVI','LFMD','LFST','LFUS','LGFA','LGFB','LGIH','LGND','LGTY','LH','LHX','LII','LILA','LILAK','LIN','LIND','LINE','LITE','LIVN','LKFN','LKQ','LLY','LLYVA','LLYVK','LMAT','LMB','LMND','LMT','LNC','LNG','LNN','LNT','LNTH','LNW','LNZA','LOAR','LOB','LOPE','LOVE','LOW','LPG','LPLA','LPRO','LPX','LQDA','LQDT','LRCX','LRMR','LRN','LSCC','LSTR','LTC','LTH','LULU','LUMN','LUNG','LUV','LVS','LW','LWLG','LXFR','LXP','LXRX','LXU','LYB','LYEL','LYFT','LYTS','LYV','LZ','LZB',
        'M','MA','MAA','MAC','MAN','MANH','MAR','MARA','MAS','MASI','MAT','MATV','MATW','MATX','MAX','MBC','MBI','MBIN','MBLY','MBUU','MBWM','MC','MCB','MCD','MCFT','MCHP','MCK','MCO','MCRI','MCW','MCY','MD','MDB','MDGL','MDLZ','MDT','MDU','MDXG','ME','MEDP','MEG','MEI','MERC','MET','META','METCV','MFA','MGEE','MGM','MGNI','MGNX','MGPI','MGRC','MGY','MHK','MHO','MIDD','MIR','MIRM','MITK','MKC','MKL','MKSI','MKTX','ML','MLAB','MLI','MLKN','MLM','MLNK','MLR','MMC','MMI','MMM','MMS','MMSI','MNKD','MNMD','MNRO','MNST','MNTK','MO','MOD','MODG','MODV','MOFG','MOGA','MOH','MORN','MOS','MOV','MP','MPB','MPC','MPLN','MPTI','MPW','MPWR','MQ','MRC','MRCY','MRK','MRNA','MRNS','MRO','MRSN','MRTN','MRVI','MRVL','MS','MSA','MSBI','MSCI','MSEX','MSFT','MSFUT','MSGE','MSGS','MSI','MSM','MSTR','MTB','MTCH','MTD','MTDR','MTG','MTH','MTN','MTRN','MTSI','MTTR','MTUS','MTW','MTX','MTZ','MU','MUR','MUSA','MUX','MVIS','MWA','MXCT','MXL','MYE','MYFW','MYGN','MYRG',
        'NABL','NAPA','NARI','NATL','NAUT','NAVI','NBBK','NBHC','NBIX','NBN','NBR','NBTB','NCLH','NCMI','NCNO','NDAQ','NDSN','NE','NECB','NEE','NEM','NEO','NEOG','NET','NEU','NEWT','NEXT','NFBK','NFE','NFG','NFLX','NGNE','NGVT','NHC','NHI','NI','NIC','NJR','NKE','NKLA','NKTX','NLOP','NLY','NMIH','NMRA','NMRK','NN','NNI','NNN','NOC','NOG','NOV','NOVA','NOVT','NOW','NPK','NPO','NR','NRC','NRDS','NRG','NRIX','NSA','NSC','NSIT','NSP','NSSC','NTAP','NTCT','NTGR','NTLA','NTNX','NTRA','NTRS','NTST','NUE','NUS','NUVB','NUVL','NVAX','NVCR','NVDA','NVEC','NVEE','NVR','NVRI','NVRO','NVST','NVT','NVTS','NWBI','NWE','NWFL','NWL','NWN','NWPX','NWS','NWSA','NX','NXPI','NXRT','NXST','NXT','NYCB','NYMT','NYT',
        'O','OABI','OBK','OC','OCFC','OCGN','OCUL','ODFL','ODP','OEC','OFG','OFIX','OFLX','OGE','OGN','OGS','OHI','OI','OII','OIS','OKE','OKLO','OKTA','OLED','OLLI','OLMA','OLN','OLO','OLP','OLPX','OMC','OMCL','OMF','OMI','ON','ONB','ONL','ONTF','ONTO','OOMA','OPCH','OPEN','OPK','ORA','ORC','ORCL','ORI','ORIC','ORLY','ORN','ORRF','OS','OSBC','OSCR','OSIS','OSK','OSPN','OSUR','OSW','OTIS','OTTR','OUST','OUT','OVBC','OVV','OWL','OXM','OXY','OZK',
        'PACB','PACS','PAG','PAHC','PANW','PAR','PARA','PARR','PATH','PATK','PAY','PAYC','PAYO','PAYX','PB','PBF','PBH','PCAR','PCB','PCG','PCH','PCOR','PCRX','PCT','PCTY','PCVX','PD','PDCO','PDFS','PDLB','PDLI','PDM','PEB','PEBO','PECO','PEG','PEGA','PEN','PENN','PEP','PETQ','PETS','PFC','PFE','PFG','PFGC','PFS','PFSI','PG','PGC','PGNY','PGR','PGRE','PH','PHAT','PHIN','PHM','PHR','PI','PII','PINC','PINS','PIPR','PJT','PK','PKG','PKST','PL','PLAB','PLAY','PLCE','PLD','PLMR','PLNT','PLOW','PLPC','PLRX','PLSE','PLTK','PLTR','PLUG','PLUS','PLXS','PLYA','PLYM','PM','PMT','PNC','PNFP','PNR','PNTG','PNW','PODD','POOL','POR','POST','POWI','POWL','PPBI','PPC','PPG','PPL','PR','PRA','PRAA','PRAX','PRCT','PRDO','PRG','PRGO','PRGS','PRI','PRIM','PRK','PRKS','PRLB','PRM','PRME','PRO','PRTA','PRU','PRVA','PSA','PSMT','PSN','PSTG','PSTL','PSX','PTC','PTCT','PTEN','PTGX','PTLO','PTON','PTVE','PUBM','PUMP','PVH','PWP','PWR','PX','PYCR','PYPL','PZZA',
        'QCOM','QCRH','QDEL','QLYS','QNST','QRTEA','QRVO','QS','QTRX','QTWO','QURE','QXO',
        'R','RAMP','RAPT','RARE','RBA','RBBN','RBC','RBCAA','RBLX','RBRK','RC','RCEL','RCKT','RCL','RCM','RCUS','RDDT','RDFN','RDN','RDNT','RDUS','RDVT','REAL','REG','REGN','RELY','REPL','RES','REVG','REX','REXR','REYN','REZI','RF','RGA','RGEN','RGLD','RGNX','RGP','RGR','RH','RHI','RHP','RICK','RIG','RILY','RIOT','RITM','RIVN','RJF','RKLB','RKT','RL','RLAY','RLI','RLJ','RMAX','RMBS','RMD','RMR','RNA','RNG','RNR','RNST','ROAD','ROCK','ROG','ROIC','ROIV','ROK','ROKU','ROL','ROOT','ROP','ROST','RPAY','RPD','RPM','RPRX','RRBI','RRC','RRR','RRX','RS','RSG','RSI','RTX','RUM','RUN','RUSHA','RUSHB','RVLV','RVMD','RVNC','RVTY','RWT','RXO','RXRX','RXST','RYAN','RYI','RYN','RYTM',
        'S','SABR','SAFE','SAFT','SAGE','SAH','SAIA','SAIC','SAM','SANA','SANM','SASR','SATS','SAVA','SAVE','SBAC','SBCF','SBGI','SBH','SBRA','SBSI','SBUX','SCHL','SCHW','SCI','SCL','SCLX','SCS','SCSC','SCVL','SD','SDGR','SEAT','SEB','SEDG','SEE','SEEL','SEG RT','SEI','SEIC','SEM','SEMR','SENS','SES','SF','SFBC','SFBS','SFIX','SFM','SFNC','SG','SGH','SGRY','SHAK','SHBI','SHC','SHCO','SHCR','SHEN','SHLS','SHO','SHOO','SHW','SHYF','SIBN','SIG','SIGA','SIGI','SILA','SIRI','SITC','SITE','SITM','SJM','SJW','SKIN','SKT','SKWD','SKX','SKY','SKYW','SLAB','SLB','SLDP','SLG','SLGN','SLM','SLNO','SLP','SLRN','SLVM','SM','SMAR','SMBC','SMBK','SMCI','SMG','SMHI','SMMT','SMP','SMPL','SMR','SMRT','SMTC','SNA','SNAP','SNBR','SNCY','SNDR','SNDX','SNEX','SNOW','SNPS','SNV','SNX','SO','SOC','SOFI','SOLV','SON','SONO','SOUN','SPB','SPCE','SPFI','SPG','SPGI','SPHR','SPNT','SPR','SPRY','SPSC','SPT','SPTN','SPXC','SQ','SQSP','SR','SRCE','SRCL','SRDX','SRE','SRG','SRI','SRPT','SRRK','SSB','SSD','SSNC','SSP','SSTK','ST','STAA','STAG','STBA','STC','STE','STEL','STEM','STEP','STER','STGW','STKL','STLD','STOK','STR','STRA','STRL','STRO','STT','STWD','STX','STZ','SUI','SUM','SUPN','SVC','SVRA','SVV','SW','SWBI','SWI','SWK','SWKS','SWTX','SWX','SXC','SXI','SXT','SYBT','SYF','SYK','SYM','SYNA','SYRE','SYY',
        'T','TALK','TALO','TAP','TARS','TBBK','TBI','TBPH','TCBI','TCBK','TDC','TDG','TDOC','TDS','TDW','TDY','TEAM','TECH','TEL','TELL','TENB','TER','TERN','TEX','TFC','TFIN','TFSL','TFX','TGI','TGLS','TGNA','TGT','TGTX','TH','THC','THFF','THG','THO','THR','THRM','THRY','THS','TILE','TIPT','TITN','TJX','TKO','TKR','TLN','TMCI','TMDX','TMHC','TMO','TMP','TMUS','TNC','TNDM','TNET','TNGX','TNL','TOL','TOST','TOWN','TPB','TPC','TPG','TPH','TPL','TPR','TPX','TR','TRC','TREE','TREX','TRGP','TRIP','TRMB','TRMK','TRML','TRN','TRNO','TRNS','TROW','TROX','TRS','TRTX','TRU','TRUP','TRV','TSCO','TSE','TSHA','TSLA','TSN','TT','TTC','TTD','TTEC','TTEK','TTGT','TTI','TTMI','TTWO','TVTX','TW','TWI','TWKS','TWLO','TWO','TWST','TXG','TXN','TXNM','TXRH','TXT','TYL','TYRA',
        'U','UA','UAA','UAL','UBER','UBSI','UCB','UCTT','UDMY','UDR','UE','UEC','UFCS','UFPI','UFPT','UGI','UHAL','UHALB','UHS','UHT','UI','ULCC','ULS','ULTA','UMBF','UMH','UNF','UNFI','UNH','UNIT','UNM','UNP','UPBD','UPS','UPST','UPWK','URBN','URI','USB','USD','USFD','USLM','USM','USNA','USPH','UTHR','UTI','UTL','UTZ','UVE','UVSP','UVV','UWMC',
        'V','VABK','VAC','VAL','VBTX','VC','VCEL','VCTR','VCYT','VECO','VEEV','VEL','VERA','VERV','VERX','VFC','VIAV','VICI','VICR','VIR','VIRT','VITL','VKTX','VLO','VLTO','VLY','VMC','VMEO','VMI','VNDA','VNO','VNOM','VNT','VOYA','VPG','VRDN','VRE','VREX','VRNS','VRNT','VRRM','VRSK','VRSN','VRT','VRTS','VRTX','VSAT','VSCO','VSEC','VSH','VST','VSTO','VSTS','VTLE','VTOL','VTR','VTRS','VTS','VUZI','VVI','VVV','VVX','VYX','VZ','VZIO',
        'W','WAB','WABC','WAFD','WAL','WASH','WAT','WAY','WBA','WBD','WBS','WCC','WD','WDAY','WDC','WDFC','WEC','WELL','WEN','WERN','WEX','WFC','WFRD','WGO','WGS','WH','WHD','WHR','WINA','WING','WK','WKC','WLDN','WLK','WLY','WM','WMB','WMG','WMK','WMS','WMT','WNC','WOLF','WOR','WOW','WPC','WRB','WRBY','WRLD','WS','WSBC','WSBF','WSC','WSFS','WSM','WSO','WSR','WST','WT','WTFC','WTI','WTM','WTRG','WTS','WTTR','WTW','WU','WULF','WVE','WW','WWD','WWW','WY','WYNN',
        'X','XEL','XERS','XHR','XMTR','XNCR','XOM','XPEL','XPER','XPO','XPOF','XPRO','XRAY','XRX','XTIA','XTSLA','XYL',
        'YELP','YETI','YEXT','YMAB','YORW','YOU','YUM',
        'Z','ZBH','ZBRA','ZD','ZETA','ZEUS','ZG','ZI','ZIMV','ZION','ZIP','ZM','ZNTL','ZS','ZTS','ZUMZ','ZUO','ZVRA','ZWS'
    ]
    return arr


def get_us_delisted_tickers():
    return ['ADRO', 'AGR', 'ALTM', 'ARCH', 'AXNX', 'AZPN', 'B', 'BFA', 'BFB', 'BOWL', 'BRKB', 'BSIG', 'CDMO', 'CEIX', 'CFB', 'CHUY', 'CTLT', 'CUR', 'CWENA', 'EDR', 'ENV', 'ESZ4', 'FAZ4', 'GATO', 
            'GEFB', 'GTXI', 'HAYN', 'HCP', 'HEIA', 'HNR', 'HTBI', 'HTLF', 'IBTX', 'INFN', 'INH', 'INST', 'JBT', 'JCS', 'LBPH', 'LENB', 'LGFA', 'LGFB', 'METCV', 'MOGA', 'MPLN', 'MRNS', 'MRO', 
            'MSFUT', 'MTTR', 'NAPA', 'NARI', 'NKLA', 'NR', 'NYCB', 'PDLI', 'PETQ', 'PFC', 'QRTEA', 'RCM', 'ROIC', 'RVNC', 'SAVE', 'SEEL', 'SEG RT', 'SGH', 'SHCR', 'SMAR', 'SQ', 'SQSP', 'SUM', 
            'TELL', 'TPX', 'TWKS', 'UHALB', 'USD', 'VSTO', 'VVI', 'VZIO', 'XTSLA', 'ZUO']


def get_us_small_cap_tickers():
    return ['AAOI', 'AAT', 'ABUS', 'ACCD', 'ACCO', 'ACEL', 'ACLS', 'ACMR', 'ADEA', 'ADNT', 'ADPT', 'ADTN', 'ADUS', 'AEO', 'AGIO', 'AGL', 'AGM', 'AGS', 'AGX', 'AGYS', 'AHCO', 'AHH', 'AIN', 'AIOT', 
            'AIR', 'AIV', 'AKBA', 'ALEX', 'ALGT', 'ALLO', 'ALNT', 'ALRS', 'ALT', 'ALX', 'AMAL', 'AMBA', 'AMBC', 'AMC', 'AMN', 'AMPH', 'AMPL', 'AMPS', 'AMR', 'AMRC', 'AMRK', 'AMSC', 'AMSF', 'AMTB', 
            'AMWD', 'ANAB', 'ANDE', 'ANGO', 'ANIP', 'AORT', 'AOSL', 'APEI', 'APGE', 'APLD', 'APOG', 'APPN', 'ARCB', 'ARDX', 'ARHS', 'ARI', 'ARIS', 'ARKO', 'ARLO', 'AROW', 'ARQT', 'ARR', 'ARRY', 'ARTNA', 
            'ARVN', 'ARWR', 'ASIX', 'ASPN', 'ASTE', 'ASTH', 'ATEC', 'ATEN', 'ATEX', 'ATKR', 'ATRC', 'ATRO', 'ATSG', 'ATUS', 'AVBP', 'AVDX', 'AVNS', 'AVO', 'AVXL', 'AXGN', 'AXL', 'AZTA', 'BAND', 'BANR', 
            'BASE', 'BBSI', 'BBW', 'BCRX', 'BDN', 'BEAM', 'BELFB', 'BFC', 'BFS', 'BFST', 'BGS', 'BHB', 'BHE', 'BHLB', 'BHRB', 'BHVN', 'BIGC', 'BJRI', 'BKD', 'BKE', 'BLBD', 'BLFS', 'BLMN', 'BLND', 'BMBL', 
            'BMRC', 'BOC', 'BRDG', 'BRKL', 'BRSP', 'BTU', 'BUSE', 'BV', 'BWB', 'BXC', 'BY', 'BZH', 'CABO', 'CAC', 'CAL', 'CARE', 'CARS', 'CASH', 'CASS', 'CBL', 'CBRL', 'CC', 'CCB', 'CCBG', 'CCNE', 'CCO', 
            'CCRN', 'CCSI', 'CDNA', 'CDRE', 'CECO', 'CELC', 'CENX', 'CERT', 'CEVA', 'CFFN', 'CGEM', 'CGON', 'CHCO', 'CHCT', 'CIFR', 'CIM', 'CLB', 'CLBK', 'CLDT', 'CLDX', 'CLFD', 'CLMT', 'CLNE', 'CLOV', 
            'CLW', 'CMCO', 'CMP', 'CMPR', 'CMTG', 'CNDT', 'CNMD', 'CNNE', 'CNOB', 'CNXN', 'COCO', 'COGT', 'COHU', 'COLL', 'COMM', 'COUR', 'CPRI', 'CRAI', 'CRCT', 'CRI', 'CRMT', 'CRSR', 'CSGS', 'CSR', 
            'CSTL', 'CSV', 'CTBI', 'CTKB', 'CTLP', 'CTO', 'CTOS', 'CTRI', 'CTS', 'CUBI', 'CVGW', 'CVI', 'CVLG', 'CWCO', 'CWH', 'CXM', 'CYH', 'DAKT', 'DAN', 'DAWN', 'DBD', 'DBRG', 'DCO', 'DCOM', 'DEA', 
            'DFIN', 'DGICA', 'DGII', 'DHC', 'DHIL', 'DIN', 'DIOD', 'DJCO', 'DK', 'DLX', 'DNA', 'DNLI', 'DNOW', 'DNTH', 'DNUT', 'DRH', 'DSGR', 'DVAX', 'DX', 'DXPE', 'DYN', 'EBF', 'ECPG', 'ECVT', 'EFC', 
            'EFSC', 'EGBN', 'EGY', 'EHAB', 'EIG', 'ELME', 'ELVN', 'EMBC', 'ENOV', 'ENVX', 'EOLS', 'EOSE', 'EPC', 'EQBK', 'ERAS', 'ERII', 'ESQ', 'ETD', 'ETNB', 'ETWO', 'EVER', 'EVGO', 'EVH', 'EVLV', 'EVRI', 
            'EWTX', 'EXPI', 'EXTR', 'EYE', 'EYPT', 'EZPW', 'FBK', 'FBMS', 'FBNC', 'FBRT', 'FCBC', 'FCF', 'FDP', 'FFIC', 'FFWM', 'FIGS', 'FIP', 'FIVN', 'FL', 'FLGT', 'FLNC', 'FLYW', 'FMBH', 'FMNB', 'FNA', 
            'FOR', 'FORM', 'FOXF', 'FPI', 'FRPH', 'FSLY', 'FTRE', 'FUBO', 'FWRD', 'FWRG', 'GABC', 'GBX', 'GCI', 'GDEN', 'GDOT', 'GDRX', 'GDYN', 'GERN', 'GES', 'GIC', 'GIII', 'GLDD', 'GMRE', 'GNE', 'GNK', 
            'GNL', 'GO', 'GOGO', 'GOOD', 'GRAL', 'GRC', 'GRPN', 'GSBC', 'GTN', 'GTX', 'GTY', 'GYRE', 'HAIN', 'HBI', 'HBNC', 'HCI', 'HCKT', 'HCSG', 'HE', 'HELE', 'HFWA', 'HI', 'HIFS', 'HLF', 'HLIO', 'HLIT', 
            'HLMN', 'HLX', 'HMN', 'HNI', 'HNST', 'HONE', 'HOPE', 'HOUS', 'HOV', 'HP', 'HPP', 'HRMY', 'HROW', 'HRTG', 'HRTX', 'HSII', 'HSTM', 'HTBK', 'HTH', 'HTLD', 'HTZ', 'HUT', 'HVT', 'HY', 'HZO', 'IART', 
            'IAS', 'IBCP', 'IBTA', 'ICFI', 'ICHR', 'IDT', 'IDYA', 'IE', 'IIIN', 'IIIV', 'IIPR', 'IMKTA', 'IMNM', 'IMXI', 'INDI', 'INN', 'INOD', 'INSW', 'INVA', 'INVX', 'IOVA', 'IRON', 'IVR', 'JACK', 'JAMF', 
            'JANX', 'JBGS', 'JBI', 'JBLU', 'JBSS', 'JELD', 'KALU', 'KALV', 'KAR', 'KE', 'KELYA', 'KFRC', 'KIDS', 'KIND', 'KLG', 'KLIC', 'KMT', 'KN', 'KODK', 'KOP', 'KOS', 'KREF', 'KRNY', 'KROS', 'KRUS', 
            'KSS', 'KURA', 'KW', 'KWR', 'KYMR', 'LAB', 'LADR', 'LAND', 'LASR', 'LBRT', 'LC', 'LEG', 'LEU', 'LGIH', 'LGND', 'LGTY', 'LILA', 'LILAK', 'LIND', 'LIVN', 'LKFN', 'LMAT', 'LMB', 'LNN', 'LOB', 
            'LPG', 'LQDA', 'LQDT', 'LTC', 'LXU', 'LYTS', 'LZ', 'LZB', 'MATW', 'MAX', 'MBC', 'MBIN', 'MBUU', 'MBWM', 'MCB', 'MCRI', 'MD', 'MDXG', 'MEG', 'MERC', 'MFA', 'MGNI', 'MGPI', 'MITK', 'ML', 'MLAB', 
            'MLKN', 'MLNK', 'MLR', 'MMI', 'MNKD', 'MNMD', 'MNRO', 'MODG', 'MOFG', 'MOV', 'MPB', 'MQ', 'MRC', 'MRTN', 'MRVI', 'MSBI', 'MSEX', 'MSGE', 'MTRN', 'MTUS', 'MTX', 'MUX', 'MXL', 'MYE', 'MYGN', 
            'MYRG', 'NABL', 'NATL', 'NAVI', 'NBBK', 'NBHC', 'NBN', 'NBR', 'NBTB', 'NCMI', 'NEO', 'NEOG', 'NEXT', 'NFBK', 'NFE', 'NGVT', 'NHC', 'NIC', 'NLOP', 'NN', 'NPK', 'NRDS', 'NRIX', 'NSSC', 'NTCT', 
            'NTGR', 'NTLA', 'NTST', 'NUS', 'NUVB', 'NVAX', 'NVCR', 'NVEE', 'NVRI', 'NVTS', 'NWBI', 'NWN', 'NWPX', 'NX', 'NXRT', 'NYMT', 'OBK', 'OCFC', 'OCUL', 'ODP', 'OEC', 'OFG', 'OFIX', 'OFLX', 'OI', 
            'OII', 'OLO', 'OLP', 'OLPX', 'OMCL', 'OMI', 'OOMA', 'OPEN', 'OPK', 'ORC', 'ORIC', 'ORRF', 'OSBC', 'OSPN', 'OSW', 'OUST', 'OXM', 'PACB', 'PACS', 'PAHC', 'PARR', 'PBF', 'PCRX', 'PCT', 'PD', 
            'PDFS', 'PDM', 'PEB', 'PEBO', 'PGC', 'PGNY', 'PGRE', 'PHAT', 'PHIN', 'PHR', 'PINC', 'PK', 'PKST', 'PL', 'PLAB', 'PLAY', 'PLOW', 'PLPC', 'PLSE', 'PLTK', 'PLUG', 'PLUS', 'PLYA', 'PLYM', 'PMT', 
            'PNTG', 'POWL', 'PPBI', 'PRA', 'PRAA', 'PRAX', 'PRDO', 'PRG', 'PRLB', 'PRM', 'PRO', 'PRTA', 'PSTL', 'PTLO', 'PTON', 'PUBM', 'PUMP', 'PWP', 'PX', 'PZZA', 'QCRH', 'QDEL', 'QNST', 'QURE', 'RAMP', 
            'RBBN', 'RBCAA', 'RC', 'RCKT', 'RCUS', 'RDFN', 'RDUS', 'RDVT', 'REAL', 'REPL', 'RES', 'REVG', 'REX', 'RGNX', 'RGR', 'RICK', 'RIG', 'RLAY', 'RLJ', 'ROCK', 'ROG', 'ROOT', 'RPAY', 'RPD', 'RRBI', 
            'RUN', 'RVLV', 'RWT', 'RXRX', 'RXST', 'RYI', 'SABR', 'SAFE', 'SAFT', 'SAGE', 'SAH', 'SANA', 'SASR', 'SBCF', 'SBGI', 'SBH', 'SBSI', 'SCHL', 'SCL', 'SCS', 'SCSC', 'SCVL', 'SD', 'SDGR', 'SEAT', 
            'SEDG', 'SEI', 'SEMR', 'SENS', 'SFIX', 'SHBI', 'SHCO', 'SHEN', 'SHLS', 'SHO', 'SHOO', 'SIBN', 'SIGA', 'SILA', 'SITC', 'SJW', 'SKWD', 'SLP', 'SMBC', 'SMBK', 'SMP', 'SMR', 'SNCY', 'SNDX', 'SOC', 
            'SONO', 'SPB', 'SPFI', 'SPHR', 'SPNT', 'SPRY', 'SPT', 'SPTN', 'SRCE', 'SRDX', 'SSTK', 'STAA', 'STBA', 'STC', 'STEL', 'STER', 'STGW', 'STKL', 'STOK', 'STRA', 'SUPN', 'SVC', 'SVRA', 'SVV', 'SWBI', 
            'SXC', 'SXI', 'SYBT', 'SYNA', 'SYRE', 'TALK', 'TALO', 'TARS', 'TBPH', 'TCBK', 'TDC', 'TDOC', 'TDW', 'TFIN', 'TGI', 'TH', 'THFF', 'THR', 'THRM', 'THRY', 'THS', 'TILE', 'TIPT', 'TITN', 'TMCI', 
            'TMP', 'TNC', 'TNDM', 'TPB', 'TPC', 'TRC', 'TREE', 'TRIP', 'TRMK', 'TRML', 'TRNS', 'TROX', 'TRS', 'TRTX', 'TRUP', 'TTGT', 'TTI', 'TTMI', 'TVTX', 'TWI', 'TWO', 'TXG', 'TYRA', 'UCTT', 'UDMY', 
            'UEC', 'UFCS', 'UFPT', 'UHT', 'ULCC', 'UMH', 'UNFI', 'UNIT', 'UPBD', 'UPWK', 'USNA', 'USPH', 'UTI', 'UTL', 'UTZ', 'UVE', 'UVSP', 'UVV', 'VAC', 'VBTX', 'VC', 'VECO', 'VEL', 'VERA', 'VERV', 
            'VICR', 'VIR', 'VITL', 'VMEO', 'VRDN', 'VRE', 'VREX', 'VRNT', 'VRTS', 'VSAT', 'VSCO', 'VSH', 'VSTS', 'VTLE', 'VTOL', 'VTS', 'VVX', 'VYX', 'WABC', 'WASH', 'WERN', 'WGO', 'WINA', 'WKC', 'WLDN',
            'WNC', 'WOLF', 'WOW', 'WRBY', 'WRLD', 'WS', 'WSR', 'WT', 'WTTR', 'WULF', 'WVE', 'WWW', 'XERS', 'XHR', 'XMTR', 'XNCR', 'XPEL', 'XPER', 'XPOF', 'XPRO', 'XRX', 'YEXT', 'YORW', 'ZD', 'ZEUS', 
            'ZIP', 'ZVRA']


def get_us_medium_cap_tickers():
    return ['AA', 'AAL', 'AAON', 'AAP', 'ABCB', 'ABG', 'ABM', 'ABR', 'ACA', 'ACAD', 'ACHC', 'ACHR', 'ACIW', 'ACLX', 'ACT', 'ACVA', 'ADC', 'ADMA', 'ADT', 'AEIS', 'AES', 'AESI', 'AGCO', 'AGNC', 'AGO', 'AHR', 
            'AI', 'AIT', 'AIZ', 'AKR', 'AKRO', 'AL', 'ALAB', 'ALB', 'ALE', 'ALG', 'ALGM', 'ALHC', 'ALIT', 'ALK', 'ALKS', 'ALKT', 'ALLY', 'ALRM', 'ALSN', 'ALTR', 'ALV', 'AM', 'AMED', 'AMG', 'AMKR', 'AMRX', 
            'AMTM', 'AN', 'ANF', 'AOS', 'APA', 'APAM', 'APG', 'APLE', 'APLS', 'APPF', 'ARMK', 'AROC', 'ARW', 'ASAN', 'ASB', 'ASGN', 'ASH', 'ASO', 'ASTS', 'ATGE', 'ATI', 'ATMU', 'ATR', 'AUB', 'AUR', 'AVA', 
            'AVAV', 'AVNT', 'AVPT', 'AVT', 'AWI', 'AWR', 'AX', 'AXS', 'AXSM', 'AXTA', 'AYI', 'AZEK', 'AZZ', 'BANC', 'BANF', 'BATRA', 'BATRK', 'BBIO', 'BBWI', 'BC', 'BCC', 'BCO', 'BCPC', 'BDC', 'BE', 'BECN', 
            'BEN', 'BERY', 'BFAM', 'BFH', 'BG', 'BGC', 'BHF', 'BILL', 'BIO', 'BKH', 'BKU', 'BL', 'BLD', 'BLKB', 'BMI', 'BNL', 'BOH', 'BOKF', 'BOOT', 'BOX', 'BPMC', 'BPOP', 'BRBR', 'BRC', 'BRKR', 'BROS', 
            'BRX', 'BRZE', 'BTSG', 'BWA', 'BWIN', 'BWXT', 'BXMT', 'BYD', 'CACC', 'CACI', 'CADE', 'CAKE', 'CALM', 'CALX', 'CAR', 'CARG', 'CART', 'CATY', 'CAVA', 'CBSH', 'CBT', 'CBU', 'CBZ', 'CCCS', 'CCK', 
            'CCOI', 'CCS', 'CDE', 'CDP', 'CE', 'CELH', 'CENTA', 'CFLT', 'CFR', 'CGNX', 'CHDN', 'CHE', 'CHEF', 'CHH', 'CHRD', 'CHX', 'CIEN', 'CIVI', 'CLF', 'CLSK', 'CLVT', 'CMA', 'CMC', 'CNK', 'CNM', 'CNO', 
            'CNS', 'CNX', 'CNXC', 'COHR', 'COLB', 'COLD', 'COLM', 'COMP', 'COOP', 'CORT', 'CORZ', 'COTY', 'CPK', 'CPRX', 'CR', 'CRC', 'CRDO', 'CRGY', 'CRK', 'CRL', 'CRNX', 'CROX', 'CRS', 'CRSP', 'CRUS', 
            'CRVL', 'CSWI', 'CTRE', 'CUBE', 'CURB', 'CUZ', 'CVBF', 'CVCO', 'CVLT', 'CWAN', 'CWEN', 'CWK', 'CWST', 'CWT', 'CXT', 'CXW', 'CYTK', 'CZR', 'DAR', 'DAY', 'DBX', 'DCI', 'DDS', 'DEI', 'DFH', 'DINO', 
            'DJT', 'DLB', 'DNB', 'DOCN', 'DOCS', 'DORM', 'DRS', 'DRVN', 'DTM', 'DV', 'DXC', 'DY', 'EAT', 'EBC', 'EE', 'EEFT', 'EGP', 'EHC', 'ELAN', 'ELF', 'EMN', 'ENPH', 'ENR', 'ENS', 'ENSG', 'ENTG', 'ENVA', 
            'EPAC', 'EPAM', 'EPR', 'EPRT', 'ESAB', 'ESE', 'ESGR', 'ESI', 'ESNT', 'ESRT', 'ESTC', 'ETSY', 'EVR', 'EVTC', 'EXAS', 'EXEL', 'EXLS', 'EXP', 'EXPO', 'FA', 'FAF', 'FBIN', 'FBP', 'FCFS', 'FCN', 
            'FCPT', 'FELE', 'FFBC', 'FFIN', 'FG', 'FHB', 'FHI', 'FHN', 'FIBK', 'FIVE', 'FIZZ', 'FLO', 'FLR', 'FLS', 'FMC', 'FN', 'FNB', 'FND', 'FOLD', 'FOUR', 'FR', 'FRME', 'FRPT', 'FRSH', 'FRT', 'FSS', 
            'FTAI', 'FTDR', 'FUL', 'FULT', 'FUN', 'FYBR', 'G', 'GAP', 'GATX', 'GBCI', 'GBTG', 'GCMG', 'GEF', 'GEO', 'GFF', 'GH', 'GHC', 'GKOS', 'GL', 'GMED', 'GMS', 'GNRC', 'GNTX', 'GNW', 'GOLF', 'GPI', 
            'GPK', 'GPOR', 'GRBK', 'GSAT', 'GSHD', 'GT', 'GTES', 'GTLB', 'GTLS', 'GVA', 'GXO', 'HAE', 'HALO', 'HAS', 'HASI', 'HAYW', 'HCC', 'HEES', 'HGV', 'HHH', 'HII', 'HIMS', 'HIW', 'HL', 'HLNE', 'HOG', 
            'HOMB', 'HQY', 'HR', 'HRB', 'HRI', 'HSIC', 'HST', 'HUBG', 'HUN', 'HURN', 'HWC', 'HWKN', 'HXL', 'IAC', 'IBOC', 'IBP', 'IBRX', 'ICUI', 'IDA', 'IDCC', 'IESC', 'IMVT', 'INDB', 'INFA', 'INGR', 'INSP', 
            'INTA', 'IONQ', 'IONS', 'IOSP', 'IPAR', 'IPG', 'IPGP', 'IRDM', 'IRT', 'IRTC', 'ITGR', 'ITRI', 'ITT', 'IVT', 'IVZ', 'JAZZ', 'JEF', 'JHG', 'JJSF', 'JOBY', 'JOE', 'JWN', 'JXN', 'KAI', 'KBH', 'KBR', 
            'KD', 'KEX', 'KFY', 'KGS', 'KMPR', 'KNF', 'KNTK', 'KNX', 'KRC', 'KRG', 'KRYS', 'KTB', 'KTOS', 'KVYO', 'LAD', 'LANC', 'LAUR', 'LAZ', 'LBTYA', 'LBTYK', 'LCID', 'LCII', 'LEA', 'LECO', 'LEVI', 'LFST', 
            'LFUS', 'LITE', 'LLYVA', 'LLYVK', 'LMND', 'LNC', 'LNTH', 'LNW', 'LOAR', 'LOPE', 'LPX', 'LRN', 'LSCC', 'LSTR', 'LTH', 'LUMN', 'LW', 'LXP', 'LYFT', 'M', 'MAC', 'MAN', 'MANH', 'MARA', 'MASI', 'MAT', 
            'MATX', 'MC', 'MCW', 'MCY', 'MDGL', 'MDU', 'MEDP', 'MGEE', 'MGM', 'MGRC', 'MGY', 'MHK', 'MHO', 'MIDD', 'MIR', 'MIRM', 'MKSI', 'MKTX', 'MLI', 'MMS', 'MMSI', 'MOD', 'MOS', 'MP', 'MPW', 'MRCY', 
            'MRNA', 'MSA', 'MSGS', 'MSM', 'MTCH', 'MTDR', 'MTG', 'MTH', 'MTN', 'MTSI', 'MTZ', 'MUR', 'MUSA', 'MWA', 'NBIX', 'NCLH', 'NCNO', 'NE', 'NEU', 'NFG', 'NHI', 'NJR', 'NMIH', 'NMRK', 'NNI', 'NNN', 
            'NOG', 'NOV', 'NOVT', 'NPO', 'NSA', 'NSIT', 'NSP', 'NUVL', 'NVST', 'NVT', 'NWE', 'NWL', 'NXST', 'NXT', 'NYT', 'OGE', 'OGN', 'OGS', 'OKLO', 'OLED', 'OLLI', 'OLN', 'OMF', 'ONB', 'ONTO', 'OPCH', 
            'ORA', 'ORI', 'OS', 'OSCR', 'OSIS', 'OSK', 'OTTR', 'OUT', 'OVV', 'OZK', 'PAG', 'PAR', 'PARA', 'PATH', 'PATK', 'PAY', 'PAYO', 'PB', 'PBH', 'PCH', 'PCOR', 'PCTY', 'PCVX', 'PDCO', 'PECO', 'PEGA', 
            'PENN', 'PFS', 'PFSI', 'PI', 'PII', 'PIPR', 'PJT', 'PLMR', 'PLNT', 'PLXS', 'PNFP', 'POR', 'POST', 'POWI', 'PR', 'PRCT', 'PRGO', 'PRGS', 'PRI', 'PRIM', 'PRK', 'PRKS', 'PRVA', 'PSMT', 'PSN', 
            'PTCT', 'PTEN', 'PTGX', 'PTVE', 'PVH', 'PYCR', 'QLYS', 'QRVO', 'QS', 'QTWO', 'QXO', 'R', 'RARE', 'RBC', 'RBRK', 'RDN', 'RDNT', 'RELY', 'REXR', 'REYN', 'REZI', 'RGEN', 'RH', 'RHI', 'RHP', 'RIOT', 
            'RITM', 'RKLB', 'RLI', 'RMBS', 'RNA', 'RNG', 'RNST', 'ROAD', 'ROIV', 'ROKU', 'RRC', 'RRR', 'RRX', 'RSI', 'RUM', 'RUSHA', 'RUSHB', 'RVMD', 'RXO', 'RYN', 'RYTM', 'S', 'SAIA', 'SAIC', 'SAM', 'SANM', 
            'SATS', 'SBRA', 'SEB', 'SEE', 'SEIC', 'SEM', 'SF', 'SFBS', 'SFNC', 'SG', 'SGRY', 'SHAK', 'SHC', 'SIG', 'SIGI', 'SIRI', 'SITE', 'SITM', 'SKT', 'SKX', 'SKY', 'SKYW', 'SLAB', 'SLG', 'SLGN', 'SLM', 
            'SLNO', 'SLVM', 'SM', 'SMG', 'SMPL', 'SMTC', 'SNDR', 'SNEX', 'SNV', 'SNX', 'SON', 'SOUN', 'SPR', 'SPSC', 'SPXC', 'SR', 'SRCL', 'SRPT', 'SRRK', 'SSB', 'SSD', 'ST', 'STAG', 'STEP', 'STR', 'STRL', 
            'STWD', 'SWI', 'SWK', 'SWKS', 'SWTX', 'SWX', 'SXT', 'TBBK', 'TCBI', 'TDS', 'TECH', 'TENB', 'TEX', 'TFSL', 'TFX', 'TGLS', 'TGNA', 'TGTX', 'THG', 'THO', 'TKR', 'TLN', 'TMDX', 'TMHC', 'TNET', 'TNL', 
            'TOWN', 'TPH', 'TR', 'TREX', 'TRN', 'TRNO', 'TTC', 'TTEK', 'TWST', 'TXNM', 'U', 'UA', 'UAA', 'UBSI', 'UCB', 'UE', 'UFPI', 'UGI', 'UMBF', 'UNF', 'UPST', 'URBN', 'USLM', 'USM', 'UWMC', 'VAL', 
            'VCEL', 'VCTR', 'VCYT', 'VERX', 'VFC', 'VIAV', 'VIRT', 'VKTX', 'VLY', 'VMI', 'VNO', 'VNOM', 'VNT', 'VOYA', 'VRNS', 'VRRM', 'VSEC', 'VTRS', 'VVV', 'W', 'WAFD', 'WAL', 'WAY', 'WBA', 'WBS', 'WCC', 
            'WD', 'WDFC', 'WEN', 'WEX', 'WFRD', 'WGS', 'WH', 'WHD', 'WHR', 'WING', 'WK', 'WLY', 'WMK', 'WMS', 'WOR', 'WSBC', 'WSC', 'WSFS', 'WTFC', 'WTM', 'WTS', 'WU', 'WWD', 'WYNN', 'X', 'XRAY', 'YELP', 
            'YETI', 'YOU', 'ZETA', 'ZI', 'ZION', 'ZWS']


def get_us_large_cap_tickers():
    return ['A', 'AAPL', 'ABBV', 'ABNB', 'ABT', 'ACGL', 'ACI', 'ACM', 'ACN', 'ADBE', 'ADI', 'ADM', 'ADP', 'ADSK', 'AEE', 'AEP', 'AFG', 'AFL', 'AFRM', 'AIG', 'AJG', 'AKAM', 'ALGN', 'ALL', 'ALLE', 'ALNY', 
            'AMAT', 'AMCR', 'AMD', 'AME', 'AMGN', 'AMH', 'AMP', 'AMT', 'AMZN', 'ANET', 'ANSS', 'AON', 'APD', 'APH', 'APO', 'APP', 'APTV', 'AR', 'ARE', 'ARES', 'ATO', 'AVB', 'AVGO', 'AVTR', 'AVY', 'AWK', 
            'AXON', 'AXP', 'AZO', 'BA', 'BAC', 'BAH', 'BALL', 'BAX', 'BBY', 'BDX', 'BIIB', 'BJ', 'BK', 'BKNG', 'BKR', 'BLDR', 'BLK', 'BMRN', 'BMY', 'BR', 'BRO', 'BSX', 'BSY', 'BURL', 'BX', 'BXP', 'C', 
            'CAG', 'CAH', 'CARR', 'CASY', 'CAT', 'CB', 'CBOE', 'CBRE', 'CCI', 'CCL', 'CDNS', 'CDW', 'CEG', 'CF', 'CFG', 'CG', 'CHD', 'CHRW', 'CHTR', 'CHWY', 'CI', 'CINF', 'CL', 'CLH', 'CLX', 'CMCSA', 'CME', 
            'CMG', 'CMI', 'CMS', 'CNA', 'CNC', 'CNH', 'CNP', 'COF', 'COIN', 'COKE', 'COO', 'COP', 'COR', 'COST', 'CPAY', 'CPB', 'CPRT', 'CPT', 'CRH', 'CRM', 'CRWD', 'CSCO', 'CSGP', 'CSL', 'CSX', 'CTAS', 
            'CTRA', 'CTSH', 'CTVA', 'CVNA', 'CVS', 'CVX', 'CW', 'D', 'DAL', 'DASH', 'DD', 'DDOG', 'DE', 'DECK', 'DELL', 'DFS', 'DG', 'DGX', 'DHI', 'DHR', 'DIS', 'DKNG', 'DKS', 'DLR', 'DLTR', 'DOC', 'DOCU', 
            'DOV', 'DOW', 'DPZ', 'DRI', 'DT', 'DTE', 'DUK', 'DUOL', 'DVA', 'DVN', 'DXCM', 'EA', 'EBAY', 'ECL', 'ED', 'EFX', 'EG', 'EIX', 'EL', 'ELS', 'ELV', 'EME', 'EMR', 'EOG', 'EQH', 'EQIX', 'EQR', 'EQT', 
            'ERIE', 'ES', 'ESS', 'ETN', 'ETR', 'EVRG', 'EW', 'EWBC', 'EXC', 'EXE', 'EXPD', 'EXPE', 'EXR', 'F', 'FANG', 'FAST', 'FCNCA', 'FCX', 'FDS', 'FDX', 'FE', 'FERG', 'FFIV', 'FI', 'FICO', 'FIS', 
            'FITB', 'FIX', 'FLEX', 'FLUT', 'FNF', 'FOX', 'FOXA', 'FSLR', 'FTI', 'FTNT', 'FTV', 'FWONA', 'FWONK', 'GD', 'GDDY', 'GE', 'GEHC', 'GEN', 'GEV', 'GGG', 'GILD', 'GIS', 'GLPI', 'GLW', 'GM', 'GME', 
            'GOOG', 'GOOGL', 'GPC', 'GPN', 'GRMN', 'GS', 'GWRE', 'GWW', 'H', 'HAL', 'HBAN', 'HCA', 'HD', 'HEI', 'HES', 'HIG', 'HLI', 'HLT', 'HOLX', 'HON', 'HOOD', 'HPE', 'HPQ', 'HRL', 'HSY', 'HUBB', 'HUBS', 
            'HUM', 'HWM', 'IBKR', 'IBM', 'ICE', 'IDXX', 'IEX', 'IFF', 'ILMN', 'INCY', 'INSM', 'INTC', 'INTU', 'INVH', 'IOT', 'IP', 'IQV', 'IR', 'IRM', 'ISRG', 'IT', 'ITCI', 'ITW', 'J', 'JBHT', 'JBL', 'JCI', 
            'JKHY', 'JLL', 'JNJ', 'JNPR', 'JPM', 'K', 'KDP', 'KEY', 'KEYS', 'KHC', 'KIM', 'KKR', 'KLAC', 'KMB', 'KMI', 'KMX', 'KNSL', 'KO', 'KR', 'KVUE', 'L', 'LAMR', 'LBRDA', 'LBRDK', 'LDOS', 'LEN', 'LH', 
            'LHX', 'LII', 'LIN', 'LINE', 'LKQ', 'LLY', 'LMT', 'LNG', 'LNT', 'LOW', 'LPLA', 'LRCX', 'LULU', 'LUV', 'LVS', 'LYB', 'LYV', 'MA', 'MAA', 'MAR', 'MAS', 'MBLY', 'MCD', 'MCHP', 'MCK', 'MCO', 'MDB', 
            'MDLZ', 'MDT', 'MET', 'META', 'MKC', 'MKL', 'MLM', 'MMC', 'MMM', 'MNST', 'MO', 'MOH', 'MORN', 'MPC', 'MPWR', 'MRK', 'MRVL', 'MS', 'MSCI', 'MSFT', 'MSI', 'MSTR', 'MTB', 'MTD', 'MU', 'NDAQ', 
            'NDSN', 'NEE', 'NEM', 'NET', 'NFLX', 'NI', 'NKE', 'NLY', 'NOC', 'NOW', 'NRG', 'NSC', 'NTAP', 'NTNX', 'NTRA', 'NTRS', 'NUE', 'NVDA', 'NVR', 'NWS', 'NWSA', 'NXPI', 'O', 'OC', 'ODFL', 'OHI', 'OKE', 
            'OKTA', 'OMC', 'ON', 'ORCL', 'ORLY', 'OTIS', 'OWL', 'OXY', 'PANW', 'PAYC', 'PAYX', 'PCAR', 'PCG', 'PEG', 'PEN', 'PEP', 'PFE', 'PFG', 'PFGC', 'PG', 'PGR', 'PH', 'PHM', 'PINS', 'PKG', 'PLD', 
            'PLTR', 'PM', 'PNC', 'PNR', 'PNW', 'PODD', 'POOL', 'PPC', 'PPG', 'PPL', 'PRU', 'PSA', 'PSTG', 'PSX', 'PTC', 'PWR', 'PYPL', 'QCOM', 'RBA', 'RBLX', 'RCL', 'RDDT', 'REG', 'REGN', 'RF', 'RGA', 
            'RGLD', 'RIVN', 'RJF', 'RKT', 'RL', 'RMD', 'RNR', 'ROK', 'ROL', 'ROP', 'ROST', 'RPM', 'RPRX', 'RS', 'RSG', 'RTX', 'RVTY', 'RYAN', 'SBAC', 'SBUX', 'SCHW', 'SCI', 'SFM', 'SHW', 'SJM', 'SLB', 
            'SMCI', 'SMMT', 'SNA', 'SNAP', 'SNOW', 'SNPS', 'SO', 'SOFI', 'SOLV', 'SPG', 'SPGI', 'SRE', 'SSNC', 'STE', 'STLD', 'STT', 'STX', 'STZ', 'SUI', 'SW', 'SYF', 'SYK', 'SYM', 'SYY', 'T', 'TAP', 'TDG', 
            'TDY', 'TEAM', 'TEL', 'TER', 'TFC', 'TGT', 'THC', 'TJX', 'TKO', 'TMO', 'TMUS', 'TOL', 'TOST', 'TPG', 'TPL', 'TPR', 'TRGP', 'TRMB', 'TROW', 'TRU', 'TRV', 'TSCO', 'TSLA', 'TSN', 'TT', 'TTD', 
            'TTWO', 'TW', 'TWLO', 'TXN', 'TXRH', 'TXT', 'TYL', 'UAL', 'UBER', 'UDR', 'UHAL', 'UHS', 'UI', 'ULS', 'ULTA', 'UNH', 'UNM', 'UNP', 'UPS', 'URI', 'USB', 'USFD', 'UTHR', 'V', 'VEEV', 'VICI', 'VLO', 
            'VLTO', 'VMC', 'VRSK', 'VRSN', 'VRT', 'VRTX', 'VST', 'VTR', 'VZ', 'WAB', 'WAT', 'WBD', 'WDAY', 'WDC', 'WEC', 'WELL', 'WFC', 'WLK', 'WM', 'WMB', 'WMG', 'WMT', 'WPC', 'WRB', 'WSM', 'WSO', 'WST', 
            'WTRG', 'WTW', 'WY', 'XEL', 'XOM', 'XPO', 'XYL', 'YUM', 'Z', 'ZBH', 'ZBRA', 'ZG', 'ZM', 'ZS', 'ZTS']


# 🔍 Example usage
if __name__ == "__main__":
    print("S&P400 mid cap wiki:")
    print(get_sp_midcap_wikipedia())
    print("S&P400 mid cap yfinance:")
    print(get_sp_midcap_yfinance())
    print("US Small Cap Tickers:")
    print(get_us_small_cap_tickers())
    print("\nUS Medium Cap Tickers:")
    print(get_us_medium_cap_tickers())
    print("\nUS Large Cap Tickers:")
    print(get_us_large_cap_tickers())