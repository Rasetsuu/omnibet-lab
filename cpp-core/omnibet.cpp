#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

struct Row {
    std::string date, league, home, away;
    int ymd = 0;
    double hg=0, ag=0, hc=0, ac=0, hs=0, as=0, hy=0, ay=0;
    bool has_c=false, has_s=false, has_y=false;
};

struct Agg {
    double m=0, gf=0, ga=0;
    double cf=0, ca=0, cm=0;
    double sf=0, sa=0, sm=0;
    double yf=0, ya=0, ym=0;
};

struct Model {
    std::vector<Row> rows;
    std::unordered_map<std::string,Agg> teams;
    double avg_g=1.20, avg_c=9.50, avg_s=24.0, avg_y=4.0;
};

struct Pred {
    double lh=0, la=0, h=0, d=0, a=0, o25=0, btts=0;
    double corners=0, o95=0, shots=0, yellows=0;
    int sh=0, sa=0;
};

static std::string trim(std::string s){
    while(!s.empty() && std::isspace(static_cast<unsigned char>(s.front()))) s.erase(s.begin());
    while(!s.empty() && std::isspace(static_cast<unsigned char>(s.back()))) s.pop_back();
    return s;
}
static std::string lower(std::string s){ for(auto& c:s)c=static_cast<char>(std::tolower(static_cast<unsigned char>(c))); return s; }
static std::string canonical(const std::string& in){
    std::string n=trim(in); std::string l=lower(n);
    if(l=="usa"||l=="united states"||l=="united states of america"||l=="u.s.a.") return "USA";
    if(l=="czech republic") return "Czechia";
    if(l=="turkey"||l=="türkiye"||l=="turkiye") return "Turkiye";
    if(l=="ivory coast"||l=="cote d'ivoire"||l=="côte d'ivoire") return "Ivory Coast";
    if(l=="dr congo"||l=="congo dr"||l=="congo democratic republic") return "DR Congo";
    if(l=="curacao"||l=="curaçao") return "Curacao";
    if(l=="cabo verde"||l=="cape verde islands") return "Cape Verde";
    if(l=="korea republic") return "South Korea";
    if(l=="bosnia-herzegovina"||l=="bosnia") return "Bosnia and Herzegovina";
    return n;
}
static std::vector<std::string> split_csv(const std::string& line){
    std::vector<std::string> out; std::string cur; bool q=false;
    for(size_t i=0;i<line.size();++i){ char c=line[i];
        if(c=='"'){ if(q && i+1<line.size() && line[i+1]=='"'){cur.push_back('"');++i;} else q=!q; }
        else if(c==','&&!q){ out.push_back(cur); cur.clear(); }
        else cur.push_back(c);
    }
    out.push_back(cur); return out;
}
static double num(const std::string& s){ std::string t=trim(s); if(t.empty()||t=="NaN"||t=="nan") return NAN; try{return std::stod(t);}catch(...){return NAN;} }
static int parse_date_ymd(const std::string& s){
    if(s.size()<10) return 0;
    try { return std::stoi(s.substr(0,4))*10000 + std::stoi(s.substr(5,2))*100 + std::stoi(s.substr(8,2)); }
    catch(...) { return 0; }
}
static double clamp(double x,double lo,double hi){ return std::max(lo,std::min(hi,x)); }
static double poisson(int k,double lam){ double p=std::exp(-lam); for(int i=0;i<k;i++) p*=lam/(i+1); return p; }

static void add_row_to_model(Model& m, const Row& r){
    m.rows.push_back(r);
    auto& H=m.teams[r.home]; H.m++; H.gf+=r.hg; H.ga+=r.ag;
    if(r.has_c){H.cf+=r.hc;H.ca+=r.ac;H.cm++;}
    if(r.has_s){H.sf+=r.hs;H.sa+=r.as;H.sm++;}
    if(r.has_y){H.yf+=r.hy;H.ya+=r.ay;H.ym++;}
    auto& A=m.teams[r.away]; A.m++; A.gf+=r.ag; A.ga+=r.hg;
    if(r.has_c){A.cf+=r.ac;A.ca+=r.hc;A.cm++;}
    if(r.has_s){A.sf+=r.as;A.sa+=r.hs;A.sm++;}
    if(r.has_y){A.yf+=r.ay;A.ya+=r.hy;A.ym++;}
}

static Model finalize_model(Model m){
    double tg=0,tc=0,ts=0,ty=0,nc=0,ns=0,ny=0;
    for(const auto& r:m.rows){
        tg += r.hg+r.ag;
        if(r.has_c){tc+=r.hc+r.ac; nc++;}
        if(r.has_s){ts+=r.hs+r.as; ns++;}
        if(r.has_y){ty+=r.hy+r.ay; ny++;}
    }
    double n=static_cast<double>(m.rows.size());
    m.avg_g=tg/std::max(1.0,2*n);
    m.avg_c=tc/std::max(1.0,nc);
    m.avg_s=ts/std::max(1.0,ns);
    m.avg_y=ty/std::max(1.0,ny);
    if(!std::isfinite(m.avg_g)||m.avg_g<=0)m.avg_g=1.2;
    if(!std::isfinite(m.avg_c)||m.avg_c<=0)m.avg_c=9.5;
    if(!std::isfinite(m.avg_s)||m.avg_s<=0)m.avg_s=24.0;
    if(!std::isfinite(m.avg_y)||m.avg_y<=0)m.avg_y=4.0;
    return m;
}

static Model build_model_from_rows(const std::vector<Row>& rows, size_t start, size_t end){
    Model m;
    end = std::min(end, rows.size());
    for(size_t i=start; i<end; ++i) add_row_to_model(m, rows[i]);
    return finalize_model(std::move(m));
}

static std::vector<Row> load_rows(const std::string& path){
    std::ifstream f(path); if(!f) throw std::runtime_error("cannot open data path: "+path);
    std::string line; std::getline(f,line); auto h=split_csv(line); std::unordered_map<std::string,int> idx;
    for(int i=0;i<(int)h.size();++i) idx[h[i]]=i;
    auto get=[&](const std::string& s){ auto it=idx.find(s); return it==idx.end() ? -1 : it->second; };
    int id=get("date"), il=get("league"), ih=get("home_team"), ia=get("away_team"), ihg=get("home_goals"), iag=get("away_goals");
    if(ih<0||ia<0||ihg<0||iag<0) throw std::runtime_error("missing mandatory columns home_team/away_team/home_goals/away_goals");
    int ihc=get("home_corners"), iac=get("away_corners"), ihs=get("home_shots"), ias=get("away_shots"), ihy=get("home_yellow"), iay=get("away_yellow");
    std::vector<Row> rows;
    while(std::getline(f,line)){
        if(line.empty()) continue;
        auto v=split_csv(line);
        if((int)v.size()<=std::max(ihg,iag)) continue;
        Row r;
        r.date = (id>=0 && id<(int)v.size()) ? v[id] : "";
        r.league = (il>=0 && il<(int)v.size()) ? v[il] : "";
        r.ymd = parse_date_ymd(r.date);
        r.home=canonical(v[ih]); r.away=canonical(v[ia]); r.hg=num(v[ihg]); r.ag=num(v[iag]);
        if(std::isnan(r.hg)||std::isnan(r.ag)) continue;
        if(ihc>=0&&iac>=0&&ihc<(int)v.size()&&iac<(int)v.size()){ r.hc=num(v[ihc]); r.ac=num(v[iac]); r.has_c=!std::isnan(r.hc)&&!std::isnan(r.ac); }
        if(ihs>=0&&ias>=0&&ihs<(int)v.size()&&ias<(int)v.size()){ r.hs=num(v[ihs]); r.as=num(v[ias]); r.has_s=!std::isnan(r.hs)&&!std::isnan(r.as); }
        if(ihy>=0&&iay>=0&&ihy<(int)v.size()&&iay<(int)v.size()){ r.hy=num(v[ihy]); r.ay=num(v[iay]); r.has_y=!std::isnan(r.hy)&&!std::isnan(r.ay); }
        rows.push_back(r);
    }
    return rows;
}

Pred predict(const Model& m, std::string home, std::string away){
    home=canonical(home); away=canonical(away); Agg dz;
    const Agg& H=m.teams.count(home)?m.teams.at(home):dz;
    const Agg& A=m.teams.count(away)?m.teams.at(away):dz;
    double avg=std::max(0.1,m.avg_g); double hm=std::max(1.0,H.m), am=std::max(1.0,A.m);
    double h_att=clamp((H.gf/hm)/avg,0.35,3.2), h_def=clamp((H.ga/hm)/avg,0.35,3.2);
    double a_att=clamp((A.gf/am)/avg,0.35,3.2), a_def=clamp((A.ga/am)/avg,0.35,3.2);
    Pred p{};
    // Baseline attack/defence multiplicative model.
    p.lh=clamp(avg*h_att*std::sqrt(a_def),0.05,4.5);
    p.la=clamp(avg*a_att*std::sqrt(h_def),0.05,4.5);
    double best=0;
    for(int i=0;i<=7;i++)for(int j=0;j<=7;j++){
        double pr=poisson(i,p.lh)*poisson(j,p.la);
        if(i>j)p.h+=pr; else if(i==j)p.d+=pr; else p.a+=pr;
        if(i+j>=3) p.o25+=pr;
        if(i>0&&j>0) p.btts+=pr;
        if(pr>best){best=pr;p.sh=i;p.sa=j;}
    }
    double total=p.h+p.d+p.a; if(total>0){p.h/=total;p.d/=total;p.a/=total;}
    double hc=H.cm?H.cf/H.cm:m.avg_c/2, aca=A.cm?A.ca/A.cm:m.avg_c/2, ac=A.cm?A.cf/A.cm:m.avg_c/2, hca=H.cm?H.ca/H.cm:m.avg_c/2;
    p.corners=clamp((hc+aca+ac+hca)/2,3,16); p.o95=1.0/(1.0+std::exp(-(p.corners-9.5)/1.8));
    double hs=H.sm?H.sf/H.sm:m.avg_s/2, asa=A.sm?A.sa/A.sm:m.avg_s/2, as=A.sm?A.sf/A.sm:m.avg_s/2, hsa=H.sm?H.sa/H.sm:m.avg_s/2;
    p.shots=clamp((hs+asa+as+hsa)/2,8,40);
    double hy=H.ym?H.yf/H.ym:m.avg_y/2, aya=A.ym?A.ya/A.ym:m.avg_y/2, ay=A.ym?A.yf/A.ym:m.avg_y/2, hya=H.ym?H.ya/H.ym:m.avg_y/2;
    p.yellows=clamp((hy+aya+ay+hya)/2,1,8);
    return p;
}

static std::vector<double> parse_doubles(std::string s){
    for(char& c:s) if(c==','||c==';') c=' ';
    std::stringstream ss(s); std::vector<double> out; double x;
    while(ss>>x) out.push_back(x);
    return out;
}

static std::vector<double> implied_multiplicative(const std::vector<double>& odds){
    std::vector<double> p; double s=0;
    for(double o: odds){ if(o<=1.0) throw std::runtime_error("decimal odds must be > 1"); p.push_back(1.0/o); s+=1.0/o; }
    for(double& x:p) x/=s;
    return p;
}
static double overround(const std::vector<double>& odds){ double s=0; for(double o:odds)s+=1.0/o; return s-1.0; }
static double kelly_fraction(double model_prob, double decimal_odds){
    double b=decimal_odds-1.0; if(b<=0) return 0.0;
    double k=(b*model_prob - (1.0-model_prob))/b;
    return std::max(0.0,k);
}
static std::map<std::string,std::string> args(int argc,char**argv){
    std::map<std::string,std::string> m; if(argc>1)m["cmd"]=argv[1];
    for(int i=2;i<argc;i++){std::string k=argv[i]; if(k.rfind("--",0)==0 && i+1<argc) m[k.substr(2)]=argv[++i];}
    return m;
}

static void print_pred(const Pred& p){
    std::cout<<std::fixed<<std::setprecision(2)
             <<"xG "<<p.lh<<"-"<<p.la<<" score "<<p.sh<<"-"<<p.sa<<"\n";
    std::cout<<"H "<<100*p.h<<" D "<<100*p.d<<" A "<<100*p.a<<"\n"
             <<"O2.5 "<<100*p.o25<<" BTTS "<<100*p.btts
             <<" corners "<<p.corners<<" O9.5 "<<100*p.o95
             <<" shots "<<p.shots<<" yellows "<<p.yellows<<"\n";
}

int main(int argc,char**argv){ try{
    auto a=args(argc,argv); std::string cmd=a.count("cmd")?a["cmd"]:"predict";
    if(cmd=="implied"){
        auto odds=parse_doubles(a.count("odds")?a["odds"]:"2.70,2.30,4.40");
        auto p=implied_multiplicative(odds);
        std::cout<<std::fixed<<std::setprecision(4)<<"margin "<<overround(odds)<<"\n";
        for(size_t i=0;i<p.size();++i) std::cout<<"p"<<i+1<<" "<<p[i]<<"\n";
        return 0;
    }
    if(cmd=="value"){
        double prob=std::stod(a.count("prob")?a["prob"]:"0.55");
        double odds=std::stod(a.count("odds")?a["odds"]:"2.10");
        double fair=1.0/odds, edge=prob-fair, k=kelly_fraction(prob,odds);
        std::cout<<std::fixed<<std::setprecision(4)<<"fair_prob "<<fair<<"\nedge "<<edge<<"\nkelly_full "<<k<<"\nkelly_quarter "<<k*0.25<<"\n";
        return 0;
    }
    std::string data=a.count("data")?a["data"]:"../data/unified_intl_matches.csv";
    auto rows=load_rows(data);
    auto full=build_model_from_rows(rows,0,rows.size());
    if(cmd=="backtest"){
        bool walk=a.count("walk-forward") && (a["walk-forward"]=="1"||a["walk-forward"]=="true");
        int min_train=a.count("min-train")?std::stoi(a["min-train"]):80;
        std::vector<Row> eval=rows;
        std::sort(eval.begin(), eval.end(), [](const Row&x,const Row&y){return x.ymd<y.ymd;});
        double acc=0,n=0,o25=0, logloss=0, brier=0;
        for(size_t i=0;i<eval.size();++i){
            if(walk && (int)i<min_train) continue;
            Model m = walk ? build_model_from_rows(eval,0,i) : full;
            auto p=predict(m, eval[i].home, eval[i].away);
            std::string pick=p.h>=p.d&&p.h>=p.a?"H":p.d>=p.a?"D":"A";
            std::string act=eval[i].hg>eval[i].ag?"H":eval[i].hg<eval[i].ag?"A":"D";
            double pa = act=="H"?p.h:act=="D"?p.d:p.a;
            pa=clamp(pa,1e-12,1.0);
            acc += pick==act; logloss += -std::log(pa);
            brier += std::pow(p.h-(act=="H"),2)+std::pow(p.d-(act=="D"),2)+std::pow(p.a-(act=="A"),2);
            o25 += ((p.o25>=0.5)==(eval[i].hg+eval[i].ag>=3)); n++;
        }
        std::cout<<std::fixed<<std::setprecision(4)
                 <<"mode "<<(walk?"walk_forward":"in_sample")<<"\n"
                 <<"matches "<<n<<"\n"
                 <<"1x2_accuracy "<<(n?acc/n:0)<<"\n"
                 <<"over25_accuracy "<<(n?o25/n:0)<<"\n"
                 <<"log_loss "<<(n?logloss/n:0)<<"\n"
                 <<"brier_1x2 "<<(n?brier/n:0)<<"\n";
        return 0;
    }
    auto p=predict(full,a.count("home")?a["home"]:"Spain",a.count("away")?a["away"]:"Cape Verde");
    print_pred(p);
    return 0;
}catch(const std::exception&e){std::cerr<<"error: "<<e.what()<<"\n"; return 1;} }
