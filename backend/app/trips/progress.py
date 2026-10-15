"""Manual progress follows route order, never elapsed time or inferred GPS."""
def state(candidate,events):
    legs=candidate['ordered_legs']
    vehicles=[(i,leg) for i,leg in enumerate(legs) if leg['type'] in ('BUS','SUBWAY')]
    records={(e['type'],str(e['leg_id'])):e for e in events if not e['excluded']}
    result={'stage':'not_departed','current_leg_id':None,'next_leg_id':None,'anchor_event_id':None,
        'actions':{'departed':legs[0]['leg_id']},'boarding_stop':None,'alighting_stop':None,'vehicle_name':None}
    terminal=next((e for e in events if e['type'] in ('missed','arrived') and not e['excluded']),None)
    if terminal:
        result.update(stage='completed' if terminal['type']=='arrived' else 'missed',
            anchor_event_id=str(terminal['id']),actions={})
        return result
    departed=records.get(('departed',legs[0]['leg_id']))
    if departed is None:return result
    anchor=departed
    for number,(index,leg) in enumerate(vehicles):
        lid=leg['leg_id'];walk=legs[index-1]['leg_id'] if index>0 else lid
        boarded=records.get(('boarded',lid));alighted=records.get(('alighted',lid))
        result.update(current_leg_id=lid,next_leg_id=lid,boarding_stop=leg['stops'][0],
            alighting_stop=leg['stops'][-1],vehicle_name=' / '.join(leg['vehicles']))
        if boarded is None:
            arrived=records.get(('approach_arrived',walk))
            result.update(stage=('transfer_waiting' if number else 'waiting') if arrived else ('transfer' if number else 'approaching'),
                anchor_event_id=str((arrived or anchor)['id']),actions={'boarded':lid,'missed':lid})
            if arrived is None:result['actions']['approach_arrived']=walk
            return result
        if alighted is None:
            result.update(stage='onboard',next_leg_id=None,anchor_event_id=str(boarded['id']),actions={'alighted':lid})
            return result
        anchor=alighted
    result.update(stage='transit_finished',current_leg_id=None,next_leg_id=None,
        anchor_event_id=str(anchor['id']),actions={'arrived':legs[-1]['leg_id']},boarding_stop=None,alighting_stop=None,vehicle_name=None)
    return result
