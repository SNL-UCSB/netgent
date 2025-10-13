from netgent.agent import NetGent

agent = NetGent()

state_repository = [
    {
        "name": "On Browser Home Page",
        "checks": [
            { "type": "url", "params": { "url": "chrome://new-tab-page/" } }
        ],
        "actions": [
            { "type": "navigate", "params": { "url": "https://www.instagram.com/" } }
        ],
        "end_state": ""
    },
    {
        "name": "Login to Account",
        "checks": [
            { "type": "text", "params": { "text": "or" } },
            { "type": "url", "params": { "url": "https://www.instagram.com/" } }
        ],
        "actions": [
            {
                "type": "type",
                "params": {
                    "by": "css selector",
                    "selector": "input._aa4b._add6._ac4d._ap35[aria-label*=\"Phone number, username, or email\"][type=\"text\"][name=\"username\"]",
                    "text": "snlclient1@gmail.com"
                }
            },
            {
                "type": "type",
                "params": {
                    "by": "css selector",
                    "selector": "input._aa4b._add6._ac4d._ap35[aria-label=\"Password\"][type=\"password\"][name=\"password\"]",
                    "text": "password"
                }
            },
            {
                "type": "click",
                "params": {
                    "by": "css selector",
                    "selector": "button._aswp._aswr._aswu._asw_._asx2[type=\"submit\"]"
                }
            }
        ],
        "end_state": ""
    },
    {
        "name": "Save Information",
        "checks": [
            { "type": "text", "params": { "text": "Save your login info?" } },
            { "type": "url", "params": { "url": "https://www.instagram.com/accounts/onetap/?next=%2F" } }
        ],
        "actions": [
            {
                "type": "click",
                "params": {
                    "by": "css selector",
                    "selector": "div.x1i10hfl.xjqpnuy.xc5r6h4.xqeqjp1.x1phubyo.xdl72j9.x2lah0s.x3ct3a4.xdj266r.x14z9mp.xat24cr.x1lziwak.x2lwn1j.xeuugli.x1hl2dhg.xggy1nq.x1ja2u2z.x1t137rt.x1q0g3np.x1a2a7pz.x6s0dn4.xjyslct.x1ejq31n.x18oe1m7.x1sy0etr.xstzfhl.x9f619.x1ypdohk.x1f6kntn.xl56j7k.x17ydfre.x2b8uid.xlyipyv.x87ps6o.x14atkfc.x5c86q.x18br7mf.x1i0vuye.xl0gqc1.xr5sc7.xlal1re.x14jxsvd.xt0b8zv.xjbqb8w.xr9e8f9.x1e4oeot.x1ui04y5.x6en5u8.x972fbf.x10w94by.x1qhh985.x14e42zd.xt0psk2.xt7dq6l.xexx8yu.xyri2b.x18d9i69.x1c1uobl.x1n2onr6.x1n5bzlp[role=\"button\"]"
                }
            }
        ],
        "end_state": ""
    },
    {
        "name": "On Instagram Home Page",
        "checks": [
            { "type": "text", "params": { "text": "Home" } },
            { "type": "url", "params": { "url": "https://www.instagram.com/" } }
        ],
        "actions": [
            { "type": "scroll", "params": { "pixels": 20, "direction": "down", "by": "tag name", "selector": "body" } },
            { "type": "scroll", "params": { "pixels": 20, "direction": "down", "by": "tag name", "selector": "body" } },
            { "type": "scroll", "params": { "pixels": 20, "direction": "down", "by": "tag name", "selector": "body" } },
            { "type": "scroll", "params": { "pixels": 20, "direction": "down", "by": "tag name", "selector": "body" } },
            { "type": "scroll", "params": { "pixels": 20, "direction": "down", "by": "tag name", "selector": "body" } },
            { "type": "scroll", "params": { "pixels": 20, "direction": "down", "by": "tag name", "selector": "body" } },
            {
                "type": "click",
                "params": {
                    "by": "css selector",
                    "selector": "div.x6s0dn4.x78zum5.xdt5ytf.xl56j7k"
                }
            }
        ],
        "end_state": "Action Completed"
    }
]

agent.run(state_repository)

