"""Query-output metrics, separate from cell-repair metrics and certification.

P/R/F1 conventions match the inspected ICDE 2026 author ClassMetrics class.
Empty positive support is flagged; a perfect numeric convention is not evidence
of effective cleaning. AUC here means normalized F1-versus-cost area, not ROC.
"""
def query_metrics(truth,predicted):
 if len(truth)!=len(predicted) or not truth:raise ValueError('nonempty aligned outputs required')
 if not all(x in (0,1,False,True) for x in truth+predicted):raise ValueError('binary full outputs required; abstentions need a declared adapter')
 tp=sum(a==b==1 for a,b in zip(truth,predicted));tn=sum(a==b==0 for a,b in zip(truth,predicted))
 fp=sum(a==0 and b==1 for a,b in zip(truth,predicted));fn=sum(a==1 and b==0 for a,b in zip(truth,predicted))
 p=tp/(tp+fp) if tp+fp else 1.0;r=tp/(tp+fn) if tp+fn else 1.0
 f=2*p*r/(p+r) if p+r else 0.0
 return dict(tp=tp,tn=tn,fp=fp,fn=fn,precision=p,recall=r,f1=f,accuracy=(tp+tn)/len(truth),
             outputs=len(truth),positive_support=tp+fn,negative_support=tn+fp,empty_positive_support=tp+fn==0)

def certification_metrics(truth,answers):
 if len(truth)!=len(answers) or not truth:raise ValueError('aligned nonempty output required')
 if not all(x in (0,1,False,True,None) for x in answers):raise ValueError('invalid answer')
 done=[(a,b) for a,b in zip(truth,answers) if b is not None]
 wrong=sum(a!=b for a,b in done)
 return dict(total=len(truth),resolved=len(done),coverage=len(done)/len(truth),
             certified_error_rate=wrong/len(done) if done else None,wrong_certifications=wrong)

def normalized_f1_cost_auc(points,max_cost):
 """Right-continuous step area: no new quality before an action is paid for."""
 if max_cost<=0 or not points or points[0][0]!=0:raise ValueError('positive budget and initial cost0 required')
 prev=-1
 for c,y in points:
  if c<prev or not 0<=y<=1:raise ValueError('ordered costs and bounded quality required')
  prev=c
 total=0.0;cost,value=points[0]
 for next_cost,next_value in points[1:]:
  if next_cost>max_cost:break
  total+=(next_cost-cost)*value;cost,value=next_cost,next_value
 total+=(max_cost-cost)*value
 return total/max_cost
