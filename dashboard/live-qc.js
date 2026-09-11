// Independent support diagnostic inspired by Titanlib; not a fault classifier.
function stationSupport(station, stations, readings, now = Date.now()) {
  const finite = v => v !== '' && v != null && Number.isFinite(Number(v));
  const latest = readings.filter(r => r.station_id === station.station_id && Number.isFinite(Date.parse(r.timestamp_utc)))
    .sort((a,b) => Date.parse(b.timestamp_utc)-Date.parse(a.timestamp_utc))[0];
  if (!latest) return {text:'No observation; spatial support unavailable.', buddies:0};
  const age = (now-Date.parse(latest.timestamp_utc))/60000;
  const count = ['temperature','pressure','humidity'].filter(k => finite(latest[k])).length;
  const distance = (a,b) => {
    const rad = x => Number(x)*Math.PI/180;
    const h = Math.sin((rad(b.latitude)-rad(a.latitude))/2)**2+Math.cos(rad(a.latitude))*Math.cos(rad(b.latitude))*Math.sin((rad(b.longitude)-rad(a.longitude))/2)**2;
    return 6371*2*Math.asin(Math.sqrt(Math.min(1,h)));
  };
  const buddies = stations.filter(s => {
    if(s.station_id===station.station_id || ![s.latitude,s.longitude,station.latitude,station.longitude,s.elevation_m,station.elevation_m].every(finite)) return false;
    if(distance(station,s)>100 || Math.abs(Number(s.elevation_m)-Number(station.elevation_m))>200) return false;
    return readings.some(r => r.station_id===s.station_id && finite(r.temperature) && Date.parse(r.timestamp_utc)<=Date.parse(latest.timestamp_utc) && Date.parse(latest.timestamp_utc)-Date.parse(r.timestamp_utc)<=3600000);
  }).length;
  return {buddies,count,age,text:`${count}/3 parameters present · ${age<0 ? 'Future timestamp: review' : Math.floor(age)+' min old'} · ${buddies} temperature buddies (100 km / 60 min / 200 m elevation). ${buddies<2 ? 'Insufficient spatial support; isolation is not a fault.' : 'Support available; agreement requires evaluation.'}`};
}
if(typeof module!=='undefined') module.exports={stationSupport};
