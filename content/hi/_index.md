---
title: "Cozystack: Kubernetes पर आधारित मुफ़्त क्लाउड प्लेटफ़ॉर्म"
description: >
  bare-metal सर्वरों के एक समूह को एक बुद्धिमान सिस्टम में बदलें, जिसमें Kubernetes क्लस्टर, Databases-as-a-Service, वर्चुअल मशीनें, लोड बैलेंसर, HTTP कैशिंग सेवाएँ और अन्य सेवाएँ आसानी से बनाने के लिए एक सरल REST API हो।

  अपना खुद का क्लाउड बनाने या किफ़ायती डेवलपमेंट एनवायरनमेंट उपलब्ध कराने के लिए Cozystack का उपयोग करें।
seo:
  title: "Cozystack — Kubernetes पर ओपन-सोर्स प्राइवेट क्लाउड"
  description: "Kubernetes पर ओपन-सोर्स क्लाउड प्लेटफ़ॉर्म: मैनेज्ड VMs, डेटाबेस, S3 स्टोरेज और GPU वर्कलोड। CNCF Sandbox प्रोजेक्ट।"
  keywords: ["private cloud", "managed kubernetes", "kubernetes platform", "cloud platform"]
source_digest: "sha256:7b7c6ca6147cb877fc4d71cba375f8be099bfd8b83c05bf5f19dff5030b4ed4e"
translation_status: current
l10n: transcreate
taglines:
  - AWS का सेल्फ-होस्टेड विकल्प
  - AI-तैयार इन्फ्रास्ट्रक्चर
  - ओपन-सोर्स VMware विकल्प
use_cases:
  - title: होस्टिंग और क्लाउड प्रोवाइडर
    situation: >
      आप VPS बेचते हैं। अब ग्राहक मैनेज्ड Kubernetes, डेटाबेस और ऑब्जेक्ट
      स्टोरेज माँगते हैं, और हर सेवा खुद बनाना एक ऐसा रोडमैप है जो कभी पूरा
      नहीं होता।
    outcome: >
      एक प्लेटफ़ॉर्म जो आपके मौजूदा हार्डवेयर को सेवाओं की सूची में बदल देता
      है: अलग-अलग टेनेंट, सेल्फ़-सर्विस प्रोविज़निंग, और एक Kubernetes-नेटिव
      API जिससे आपकी बिलिंग जुड़ सकती है।
    link: /docs/guides/use-cases/public-cloud/
    link_text: पब्लिक क्लाउड बनाना
  - title: VMware छोड़ रही टीमें
    situation: >
      स्थायी लाइसेंस अब नहीं रहे, नवीनीकरण की सीमाएँ आ गईं, और VMs को अब भी
      कहीं चलना है — वहाँ, जहाँ नियंत्रण आपका हो।
    outcome: >
      वर्चुअल मशीनें और कंटेनर एक ही क्लस्टर में, आपके अपने सर्वरों पर, लाइव
      माइग्रेशन और रेप्लिकेटेड स्टोरेज के साथ — और माइग्रेशन एक टूल है, पूरा
      दोबारा लिखना नहीं।
    link: /docs/guides/use-cases/private-cloud/
    link_text: प्राइवेट क्लाउड बनाना
  - title: प्लेटफ़ॉर्म टीमें
    situation: >
      डेवलपर डेटाबेस, क्लस्टर या एनवायरनमेंट के लिए टिकट खोलते हैं, और इन सबके
      लिए प्लेटफ़ॉर्म टीम ही अड़चन बन जाती है।
    outcome: >
      डेवलपर जो चाहिए उसे Kubernetes रिसोर्स की तरह माँगते हैं और मिनटों में पा
      जाते हैं — आपकी तय की गई कोटा-सीमा के भीतर, किसी और के क्लाउड पर अकाउंट
      बनाए बिना।
    link: /docs/guides/use-cases/kubernetes-distribution/
    link_text: Kubernetes डिस्ट्रिब्यूशन के रूप में
  - title: विश्वविद्यालय और शोध
    situation: >
      हर समूह अपना क्लस्टर और GPU में हिस्सा चाहता है, और इनमें से किसी का भी
      प्रशासन कोई नहीं करना चाहता।
    outcome: >
      साझा हार्डवेयर पर हर समूह या हर कोर्स के लिए सचमुच अलग क्लस्टर, उनके बीच
      GPU का बँटवारा, और ऐसा एनवायरनमेंट जिसे अगले सत्र में रिपॉज़िटरी से फिर
      से खड़ा किया जा सके।
  - title: सरकारी और विनियमित क्षेत्र
    situation: >
      डेटा आपके अधिकार-क्षेत्र से बाहर नहीं जा सकता, और बाहरी कंट्रोल प्लेन पर
      निर्भर रहने की अनुमति आपको नहीं है।
    outcome: >
      पूरा प्लेटफ़ॉर्म आपके अपने हार्डवेयर पर चलता है, नियंत्रण-पथ में कोई बाहरी
      SaaS नहीं, और हर घटक ओपन सोर्स है जिसका ऑडिट आप कर सकते हैं।
  - title: टेलीकॉम और एज
    situation: >
      नेटवर्क फ़ंक्शन अब भी वर्चुअल मशीनों के रूप में आते हैं जबकि हर नई चीज़
      कंटेनर के रूप में — और अंत में दोनों अलग-अलग स्टैक पर चले जाते हैं।
    outcome: >
      दोनों एक ही प्लेटफ़ॉर्म पर, उस नेटवर्किंग के साथ जो डेटाप्लेन को चाहिए —
      केंद्रीय साइट से लेकर छोटे एज क्लस्टरों तक।

benefits:
  - title: API-first
    icon: fas fa-code
    description: >
      Cozystack, Kubernetes पर आधारित है और इसके API के साथ घनिष्ठ अंतःक्रिया पर ज़ोर देता है। यह सभी तत्वों को किसी सुंदर UI या कस्टमाइज़ेशन के पीछे पूरी तरह छिपाने का लक्ष्य नहीं रखता। इसके बजाय यह एक मानक इंटरफ़ेस देता है और उपयोगकर्ताओं को बुनियादी प्रिमिटिव्स के साथ काम करना सिखाता है।
  - title: मानकीकरण और एकीकरण
    icon: fas fa-certificate
    description: >
      प्लेटफ़ॉर्म के सभी घटक उद्योग में व्यापक रूप से ज्ञात, सिद्ध ओपन-सोर्स टूल और तकनीकों पर आधारित हैं।
      हम सबसे स्थापित और परखे हुए तरीकों का उपयोग करने का प्रयास करते हैं, जिससे पूरा प्लेटफ़ॉर्म बहुत सरल बनता है और वेंडर लॉक-इन से बचा जा सकता है।
  - title: प्रतिस्पर्धा नहीं, सहयोग
    icon: fas fa-handshake
    description: >
      हमें अपने समुदाय पर गर्व है और हम इसके आसपास के प्रोजेक्ट्स के साथ निकटता से काम करते हैं।
      अगर हम कोई ऐसी प्लेटफ़ॉर्म सुविधा बनाते हैं जो किसी upstream प्रोजेक्ट में उपयोगी हो सकती है,
      तो हम उसे प्लेटफ़ॉर्म में रखने के बजाय उस प्रोजेक्ट में योगदान देना पसंद करते हैं।
features:
  - title: इंस्टॉल करना आसान
    icon: fas fa-wrench
    description: >
      [talos-bootstrap](https://github.com/cozystack/talos-bootstrap/) के साथ हम सबसे आसान इंस्टॉलेशन तरीका देते हैं,
      जिससे आप खाली डेटा सेंटर के सर्वरों पर PXE या ISO विधि से Cozystack बूटस्ट्रैप कर सकते हैं।
      immutable OS का उपयोग सिस्टम की संगति बनाए रखने और यह सुनिश्चित करने में मदद करता है कि सब कुछ अपेक्षा के अनुसार काम करे।
  - title: एकीकृत करना आसान
    icon: fas fa-plug
    description: >
      हम एक नेटिव Kubernetes RESTful API देते हैं, जो अपनी डिक्लेरेटिव प्रकृति के लिए व्यापक रूप से जाना जाता है।
      इसलिए अपने बिलिंग के साथ एकीकरण के लिए इतना ही पर्याप्त है कि आप अपने सिस्टम को इच्छित सेवा बताने वाला एक विशिष्ट YAML मैनिफ़ेस्ट Kubernetes API को भेजने का निर्देश दें।
      बाकी काम Cozystack आपके लिए कर देगा।
  - title: विस्तार करना आसान
    icon: fas fa-up-right-and-down-left-from-center
    description: >
      प्लेटफ़ॉर्म का प्रत्येक पैकेज YAML फ़ाइलों के एक समूह से बना होता है। इसलिए Kubernetes प्रिमिटिव्स से परिचित कोई भी व्यक्ति प्लेटफ़ॉर्म को संशोधित या विस्तारित कर सकता है। पैकेज डिलीवरी को सुप्रसिद्ध और व्यापक रूप से उपयोग किया जाने वाला टूल FluxCD भरोसेमंद ढंग से संभालता है।
  - title: उच्च प्रदर्शन, कम ओवरहेड
    icon: fas fa-gauge-high
    description: >
      हम प्रदर्शन की परवाह करते हैं। इसीलिए हम स्थिरता और कार्यक्षमता में संतुलन रखते हुए सबसे उच्च-प्रदर्शन वाली तकनीकें अपनाते हैं।
      इसके अलावा, हमारा अनूठा टेनेंट मॉडल Control Plane के लिए क्लाउड संसाधनों का कुशल आवंटन सक्षम करता है, जिससे लागत-दक्षता और आवश्यक स्तर की सुरक्षा सुनिश्चित होती है।
  - title: अंतर्निहित मॉनिटरिंग और अलर्ट
    icon: fas fa-area-chart
    description: >
      प्रत्येक सेवा का प्रत्येक इंस्टेंस पूर्व-कॉन्फ़िगर किए गए डैशबोर्ड और अलर्ट के एक सेट के साथ आता है।
      आप प्रत्येक टेनेंट के लिए अलग मॉनिटरिंग हब बना सकते हैं या उन्हें एक में जोड़ सकते हैं।
  - title: ऐप प्रबंधन के लिए अंतर्निहित UI
    icon: fas fa-window-maximize
    description: >
      हालाँकि प्लेटफ़ॉर्म का प्राथमिक लक्ष्य एक सुंदर API देना है, फिर भी इसमें एप्लिकेशन परिनियोजित करने के लिए एक डैशबोर्ड भी है।
      यह वेब UI प्लेटफ़ॉर्म में तेज़ी से उतरने में मदद करता है और इसकी क्षमताओं का दृश्य प्रदर्शन करता है।
---

<div class="hero-gitops">
  {{% blocks/hero title="Cozystack: Kubernetes पर आधारित मुफ़्त क्लाउड प्लेटफ़ॉर्म" color="primary"
  height="auto" link_title="शुरुआत करें" link_url="/hi/docs/v1.4/getting-started/" %}}
  bare-metal सर्वरों के एक समूह को एक बुद्धिमान सिस्टम में बदलें, जिसमें Kubernetes क्लस्टर, Databases-as-a-Service, वर्चुअल मशीनें, लोड बैलेंसर, HTTP कैशिंग सेवाएँ और अन्य सेवाएँ आसानी से बनाने के लिए एक सरल REST API हो।

  अपना खुद का क्लाउड बनाने या किफ़ायती डेवलपमेंट एनवायरनमेंट उपलब्ध कराने के लिए Cozystack का उपयोग करें।

  {{% /blocks/hero %}}

  <div class="lead-flux">
  {{< blocks/lead >}}
  {{< /blocks/lead >}}
  </div>
</div>

<!-- Screenshot Gallery -->
{{< home/screenshot-gallery >}}

<!-- Live Demo -->
<div class="section-live-demo">
{{< blocks/lead color="primary" >}}
<h2 class="section-label">कुछ भी इंस्टॉल करने से पहले कंसोल देखें</h2>

<p class="live-demo-lead">Cozystack का असली डैशबोर्ड, पूरी तरह आपके ब्राउज़र में चलता हुआ — न क्लस्टर, न साइनअप, न सेटअप। मार्केटप्लेस देखें, मैनेज्ड सेवाएँ खोलें, कंसोल में क्लिक करके घूमें। यह असली UI ही है, बस डेमो डेटा के साथ।</p>

<div class="live-demo-cta"><a class="btn btn-lg btn-primary" href="/demo/">लाइव डेमो खोलें &rarr;</a></div>
{{< /blocks/lead >}}
</div>

<!-- Benefits & Features -->

{{< home/use-cases >}}

{{< home/benefits >}}

{{< home/features >}}

<!-- Community -->
<div class="section-community">
  {{< blocks/lead color="dark" >}}
  <h2 class="section-label">
  समुदाय
  </h2>

  <p>Cozystack के विकास में हमारे समुदाय के अटूट समर्थन और योगदान की हम गहरी सराहना करते हैं।<br/> हमारे समुदाय से जुड़ें और हमारी यात्रा का हिस्सा बनें।</p>

  {{< /blocks/lead >}}

  <div class="subsection-community-row">
  {{< blocks/section color="dark" type="community-row">}}

  {{< home/community icon="fab fa-github" title="GitHub Discussions" >}}
  <a target="_blank" rel="noopener noreferrer" href="https://github.com/cozystack/cozystack/discussions">GitHub Discussions में चर्चा में शामिल हों</a>। Cozystack से जुड़ी हर बात — विनिर्देशों और फ़ीचर प्लानिंग से लेकर Show &amp; Tell तक — यहीं होती है।

  {{< /home/community >}}

  {{< home/community icon="fab fa-slack" title="Slack" >}}
  अगर आप Cozystack टीम और समुदाय से रीयल-टाइम में बात करना चाहते हैं, तो Slack पर हमसे जुड़ें। सबको जानने का यह एक बढ़िया तरीका है।

  एक <a target="_blank" rel="noopener noreferrer" href="https://slack.kubernetes.io/">Slack आमंत्रण</a> प्राप्त करें, या <a target="_blank" rel="noopener noreferrer" href="https://kubernetes.slack.com/messages/cozystack"><code>#cozystack</code> चैनल</a> पर जाएँ।

  {{< /home/community >}}

  {{< home/community icon="fa fa-paper-plane" title="Telegram" >}}
  हमारा Telegram पर भी एक बड़ा समुदाय है। साथी उपयोगकर्ताओं से जुड़ने, सवाल पूछने और नवीनतम समाचार व विकास से अपडेट रहने के लिए <a target="_blank" rel="noopener noreferrer" href="https://t.me/cozystack/">@cozystack</a> ग्रुप चैट से जुड़ें।
  {{< /home/community >}}

  {{< /blocks/section >}}
  </div>

</div>

{{< home/cncf >}}
