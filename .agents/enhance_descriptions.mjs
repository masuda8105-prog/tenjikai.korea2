import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const masterPath = path.join(root, 'product_master_multilingual.csv');
const auditPath = path.join(root, '.agents', 'description_evidence_audit.csv');

function parseCsv(text) {
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
      continue;
    }
    if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      row.push(field);
      field = '';
    } else if (ch === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (ch !== '\r') {
      field += ch;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function stringifyCsv(headers, objects) {
  const esc = (value) => {
    const s = String(value ?? '');
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [
    headers.map(esc).join(','),
    ...objects.map((obj) => headers.map((h) => esc(obj[h])).join(',')),
  ].join('\r\n') + '\r\n';
}

function rowsToObjects(rows) {
  const headers = rows[0];
  return {
    headers,
    objects: rows.slice(1).filter((r) => r.some((v) => v !== '')).map((r) => {
      const obj = {};
      headers.forEach((h, i) => {
        obj[h] = r[i] ?? '';
      });
      return obj;
    }),
  };
}

function compact(text) {
  return String(text ?? '')
    .replace(/\s+/g, ' ')
    .replace(/ \|\| /g, ' || ')
    .trim();
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function findSnippets(row) {
  const memo = compact(row.PDF抽出メモ || '');
  if (!memo) return [];
  const code = String(row.品番 || '').trim();
  const name = String(row.商品名_JA || '').trim().replace(/\(.*/, '');
  const patterns = [];
  if (code) {
    patterns.push({ re: new RegExp(`No\\.?\\s*${escapeRegExp(code)}(?![0-9A-Za-z-])`, 'g'), score: 20 });
    patterns.push({ re: new RegExp(`(?<![0-9A-Za-z-])${escapeRegExp(code)}(?![0-9A-Za-z-])`, 'g'), score: 4 });
  }
  if (name && name.length > 2) {
    patterns.push({ re: new RegExp(escapeRegExp(name), 'g'), score: 3 });
  }
  const found = [];
  for (const { re, score } of patterns) {
    for (const m of memo.matchAll(re)) {
      const start = Math.max(0, m.index - 180);
      const end = Math.min(memo.length, m.index + 360);
      const snippet = memo.slice(start, end).trim();
      const keywordScore = [
        '用途', '特徴', '調整', '固定', '交換', '補修', 'クリングス', 'パット',
        'テンプル', 'ブリッジ', 'モダン', 'リム', '智固定', 'ツーポイント',
      ].reduce((sum, k) => sum + (snippet.includes(k) ? 2 : 0), 0);
      found.push({ snippet, score: score + keywordScore });
    }
  }
  const unique = new Map();
  for (const item of found.sort((a, b) => b.score - a.score)) {
    const key = item.snippet.slice(0, 90);
    if (!unique.has(key)) unique.set(key, item.snippet);
    if (unique.size >= 4) break;
  }
  return [...unique.values()];
}

const templates = {
  ja: {
    pliers_klings_adjustment: {
      usage: 'クリングス調整',
      benefit: '細かな角度をつかんで鼻当たりを整えやすい',
      summary: 'クリングスやパット足の細かな角度調整に使うヤットコです。先端形状に合わせてつかみ分けでき、鼻当たりや掛け心地を整えやすくします。',
    },
    pliers_pad_box_adjustment: {
      usage: '箱蝶・ワンタッチパッド調整',
      benefit: 'パッド金具を安定して保持しやすい',
      summary: '箱蝶やワンタッチ式パッドの調整に使うヤットコです。パッド周りを安定して保持し、角度調整や交換作業を進めやすくします。',
    },
    pliers_push_lock_pad_adjustment: {
      usage: 'プッシュロックパッド調整',
      benefit: '金具の傷やカラー剥げを抑えながら調整しやすい',
      summary: 'プッシュロックパッド専用の調整ヤットコです。金具を点ではなく面で挟み、カラー剥げや傷を抑えながら狭いリムとパッドの間でも角度調整しやすくします。',
    },
    pliers_twin_pad_arm_adjustment: {
      usage: '2本ダキ足パッド調整',
      benefit: '抱き込み部分の緩みを防ぎながら作業しやすい',
      summary: '2本ダキ足パッド専用の調整ヤットコです。取付金具とパッドを包み込んで保持し、調整時に起こりやすい抱き込み部分の緩みを防ぎながら作業できます。',
    },
    pliers_built_in_pad_adjustment: {
      usage: 'ネジ掴み・ビルトインパッド調整',
      benefit: '細かなパッド金具を安定してつかみやすい',
      summary: 'ネジ掴みやビルトインパッドの調整に使うヤットコです。細かな金具やパッド周りを安定して保持し、修理・調整作業を進めやすくします。',
    },
    pliers_joint_hold: {
      usage: '智固定・テンプル調整サポート',
      benefit: '智を固定してテンプル調整を安定させやすい',
      summary: 'テンプル調整時に智を固定するためのヤットコです。智をくぼみに入れて保持し、フレームを安定させながら角度調整を行いやすくします。',
    },
    pliers_two_point_hold: {
      usage: 'ツーポイント固定・テンプル開き調整',
      benefit: 'レンズを外さずにテンプル開きを調整しやすい',
      summary: 'ツーポイントフレームを固定してテンプル開きを調整するヤットコです。レンズを外さずに保持でき、作業時のズレや負担を抑えやすくします。',
    },
    pliers_temple_angle: {
      usage: 'テンプル角度・前傾角調整',
      benefit: '掛け位置と見え方を整えやすい',
      summary: 'テンプル角度や前傾角を調整するヤットコです。顔幅や掛け位置に合わせて、フィット感と見え方を整えやすくします。',
    },
    pliers_temple_opening: {
      usage: 'テンプル開き調整',
      benefit: '左右の開きと掛け心地を整えやすい',
      summary: 'テンプルの開き具合を調整するヤットコです。左右の開きや掛け心地を確認しながら、フレームを安定して整えやすくします。',
    },
    pliers_bridge_angle: {
      usage: 'ブリッジ角度調整',
      benefit: 'フレーム前面のバランスを整えやすい',
      summary: 'ブリッジ角度を調整するためのヤットコです。左右レンズの位置関係やフレーム前面のバランスを整え、掛け心地の調整に役立ちます。',
    },
    pliers_modern_bending: {
      usage: 'モダン曲げ調整',
      benefit: '強い力をピンポイントにかけて曲げやすい',
      summary: 'モダン曲げ調整に使うヤットコです。モダンをあてがって握り込むことで、曲げにくい金手などもピンポイントに力をかけて調整しやすくします。',
    },
    pliers_rim_shape: {
      usage: 'リム形状調整',
      benefit: 'リム形状を整えてレンズ合わせをしやすい',
      summary: 'リムのアール付けやアール修正、ナイロール型直しに使うヤットコです。リム形状を整え、レンズ合わせの精度を上げやすくします。',
    },
    pliers_rimless_screw_cutter: {
      usage: 'ツーポイントネジ長さ調整',
      benefit: 'ネジを必要な長さに整えやすい',
      summary: 'ツーポイントフレーム用のネジ切りヤットコです。先端の穴にネジを差し込んで切り、必要な長さに整えやすくします。',
    },
    pliers_cutting: {
      usage: '切断・喰い切り作業',
      benefit: '小さな部品や線材を狙った位置で処理しやすい',
      summary: '切断や喰い切り作業に使う工具です。小さな部品や線材を狙った位置で処理しやすく、修理・加工の仕上げに役立ちます。',
    },
    pliers_replacement_tip: {
      usage: 'ヤットコ先端の交換・保護',
      benefit: 'フレームや部品への傷を抑えやすい',
      summary: '対象ヤットコの先端に取り付ける交換用部品です。フレームや部品に当たる面を保護し、傷を抑えながら調整しやすくします。',
    },
    pliers_guard_arm_install: {
      usage: 'ガードアーム取付',
      benefit: '二本足部品を保持して圧入しやすい',
      summary: 'ガードアームなどの二本足部品を保持して取り付けるヤットコです。先端をつかんだまま加熱・圧入しやすく、取付位置を安定させやすくします。',
    },
    pliers_generic: {
      usage: '眼鏡フレーム調整・部品保持',
      benefit: '狙った部分を安定してつかみやすい',
      summary: '眼鏡フレームの調整や部品保持に使うヤットコです。先端形状に合わせて使い分けることで、狙った部分を安定してつかみやすくします。',
    },
    processing_file: {
      usage: '加工・研磨',
      benefit: '削りや仕上げ作業を進めやすい',
      summary: '眼鏡フレームや部品の削り・仕上げに使う加工用品です。形状や用途に合わせて選ぶことで、細かな調整や研磨作業を進めやすくします。',
    },
    pad_arm_part: {
      usage: '鼻パッド足の交換・補修',
      benefit: '必要な側や形状を選んで補修しやすい',
      summary: '鼻パッド周りの足部品を交換・補修するためのパーツです。左右や取付形状に合わせて選べるため、必要な部分だけを補修しやすくします。',
    },
    screwdriver_handle: {
      usage: 'ドライバー柄の交換・兼用',
      benefit: '対応する替え先を使い分けやすい',
      summary: '対応する替え先と組み合わせて使うドライバー柄です。作業内容に合わせて先端を使い分けられ、修理・調整工具をまとめやすくします。',
    },
  },
};

templates.en = {
  pliers_klings_adjustment: ['klings / pad-arm adjustment', 'helps grip small angles and refine nose-pad fit', 'Pliers for fine adjustment around klings and pad arms. The tip shape helps grip small parts accurately and refine nose-pad fit.'],
  pliers_pad_box_adjustment: ['box hinge / push-in pad adjustment', 'helps hold pad hardware steadily', 'Pliers for adjusting box-hinge or push-in nose pads. They help hold the pad area steadily for angle adjustment and replacement work.'],
  pliers_push_lock_pad_adjustment: ['push-lock pad adjustment', 'helps adjust while reducing scratches and color loss', 'Dedicated pliers for push-lock pad adjustment. They hold the hardware by surface contact, helping reduce scratches and color loss in narrow spaces.'],
  pliers_twin_pad_arm_adjustment: ['twin pad-arm adjustment', 'helps prevent looseness while adjusting', 'Dedicated pliers for twin pad-arm pads. They wrap and hold the mounting hardware and pad, helping prevent looseness during adjustment.'],
  pliers_built_in_pad_adjustment: ['screw-grip / built-in pad adjustment', 'helps grip small pad hardware steadily', 'Pliers for screw-grip and built-in pad adjustment. They help hold small hardware around the pad area steadily during repair and fitting work.'],
  pliers_joint_hold: ['joint holding and temple adjustment support', 'helps stabilize the joint during temple adjustment', 'Pliers for holding the eyewire joint during temple adjustment. They support the frame so angle work can be done more steadily.'],
  pliers_two_point_hold: ['two-point frame holding and temple opening adjustment', 'helps adjust temple opening without removing lenses', 'Pliers for holding two-point frames while adjusting temple opening. They help keep the frame steady without removing the lenses.'],
  pliers_temple_angle: ['temple angle and pantoscopic tilt adjustment', 'helps refine fit position and vision balance', 'Pliers for adjusting temple angle and pantoscopic tilt. They help refine the wearing position, fit, and visual balance.'],
  pliers_temple_opening: ['temple opening adjustment', 'helps balance left and right temple opening', 'Pliers for adjusting temple opening. They help balance the left and right sides and stabilize the frame fit.'],
  pliers_bridge_angle: ['bridge-angle adjustment', 'helps balance the front of the frame', 'Pliers for adjusting bridge angle. They help align the front balance of the frame and support fit adjustments around the lens position.'],
  pliers_modern_bending: ['temple-tip bending', 'helps apply focused force for difficult bends', 'Pliers for bending temple tips. They help apply focused force to areas that are difficult to bend by hand.'],
  pliers_rim_shape: ['rim-shape adjustment', 'helps refine rim shape for lens fitting', 'Pliers for rim curve and shape correction, including nylor-style work. They help refine rim shape for more accurate lens fitting.'],
  pliers_rimless_screw_cutter: ['two-point screw length adjustment', 'helps trim screws to the needed length', 'Screw-cutting pliers for two-point frames. The screw can be inserted into the tip hole and cut to the needed length.'],
  pliers_cutting: ['cutting and end-cutting work', 'helps process small parts or wire at the target point', 'A tool for cutting or end-cutting work. It helps process small parts or wire at the target point during repair and finishing.'],
  pliers_replacement_tip: ['plier-tip replacement and protection', 'helps reduce scratches on frames and parts', 'A replacement part for the target plier tip. It protects the contact surface and helps reduce scratches during adjustment.'],
  pliers_guard_arm_install: ['guard-arm installation', 'helps hold two-leg parts for insertion', 'Pliers for holding and installing two-leg parts such as guard arms. They help keep the part steady during heating and press-in work.'],
  pliers_generic: ['eyewear frame adjustment and parts holding', 'helps grip the target area steadily', 'Pliers for eyewear frame adjustment and parts holding. Different tip shapes help grip the target area steadily.'],
  processing_file: ['processing and polishing', 'helps with fine grinding and finishing work', 'A processing supply for grinding and finishing eyewear frames or parts. Choose the shape by task to support fine adjustment and polishing.'],
  pad_arm_part: ['nose-pad arm replacement and repair', 'helps repair only the needed side or shape', 'A part for replacing or repairing nose-pad arm areas. It can be selected by side and mounting shape for targeted repair.'],
  screwdriver_handle: ['replaceable screwdriver handle', 'helps switch compatible tips by task', 'A screwdriver handle used with compatible replaceable tips. It helps switch tip types by repair or adjustment task.'],
};

templates.zh = {
  pliers_klings_adjustment: ['托叶臂/鼻托脚调整', '便于夹住细小角度并调整鼻托贴合', '用于托叶臂和鼻托脚细微角度调整的钳子。可按前端形状稳定夹持小部位，便于调整鼻托贴合与佩戴感。'],
  pliers_pad_box_adjustment: ['盒式/插入式鼻托调整', '便于稳定夹持鼻托金具', '用于盒式或插入式鼻托调整的钳子。可稳定夹持鼻托周边，便于角度调整和更换作业。'],
  pliers_push_lock_pad_adjustment: ['Push-lock鼻托调整', '调整时有助于减少划伤和掉色', 'Push-lock鼻托专用调整钳。以面接触夹持金具，有助于在狭窄位置减少划伤和掉色并完成角度调整。'],
  pliers_twin_pad_arm_adjustment: ['双脚鼻托调整', '便于防止抱合部位松动', '双脚鼻托专用调整钳。可包住安装金具和鼻托进行保持，有助于在调整时防止抱合部位松动。'],
  pliers_built_in_pad_adjustment: ['螺丝夹持/内置鼻托调整', '便于稳定夹持细小鼻托金具', '用于螺丝夹持和内置鼻托调整的钳子。可稳定保持鼻托周边小金具，便于修理和调校。'],
  pliers_joint_hold: ['庄头固定/镜腿调整辅助', '便于固定庄头并稳定调整镜腿', '用于镜腿调整时固定庄头的钳子。可保持镜架稳定，便于进行角度调整。'],
  pliers_two_point_hold: ['两点框固定/镜腿开合调整', '便于不取下镜片调整镜腿开合', '用于固定两点式镜架并调整镜腿开合的钳子。无需取下镜片即可保持镜架，减少作业时偏移。'],
  pliers_temple_angle: ['镜腿角度/前倾角调整', '便于调整佩戴位置和视线平衡', '用于调整镜腿角度和前倾角的钳子。可根据脸宽和佩戴位置，调整贴合感和视线平衡。'],
  pliers_temple_opening: ['镜腿开合调整', '便于整理左右开合和佩戴感', '用于调整镜腿开合的钳子。可一边确认左右开合和佩戴感，一边稳定调整镜架。'],
  pliers_bridge_angle: ['镜桥角度调整', '便于整理镜架前面平衡', '用于调整镜桥角度的钳子。可帮助整理左右镜片位置关系和镜架前面平衡，便于佩戴感调整。'],
  pliers_modern_bending: ['脚套弯曲调整', '便于对难弯位置集中施力', '用于脚套弯曲调整的钳子。通过抵住脚套并握紧，可对难以弯曲的部位集中施力。'],
  pliers_rim_shape: ['镜圈形状调整', '便于整理镜圈形状以配合镜片', '用于镜圈弧度修正和尼龙丝镜架整形的钳子。可整理镜圈形状，提升配片精度。'],
  pliers_rimless_screw_cutter: ['两点框螺丝长度调整', '便于把螺丝修剪到需要长度', '两点式镜架用切螺丝钳。可将螺丝插入前端孔位后切断，便于调整到所需长度。'],
  pliers_cutting: ['切断/端切作业', '便于在目标位置处理小部件和线材', '用于切断和端切作业的工具。便于在目标位置处理小部件或线材，适合修理和加工收尾。'],
  pliers_replacement_tip: ['钳子前端更换/保护', '有助于减少镜架和部件划伤', '安装在对应钳子前端的更换部件。可保护接触面，调整时有助于减少镜架和部件划伤。'],
  pliers_guard_arm_install: ['护臂安装', '便于夹持两脚部件并压入', '用于夹持并安装护臂等两脚部件的钳子。可在加热和压入时稳定保持部件位置。'],
  pliers_generic: ['眼镜架调整/部件夹持', '便于稳定夹住目标部位', '用于眼镜架调整和部件夹持的钳子。可按前端形状分用，稳定夹住目标部位。'],
  processing_file: ['加工/研磨', '便于细部削磨和收尾', '用于眼镜架或部件削磨、收尾的加工用品。可按形状和用途选择，支持细部调整和研磨作业。'],
  pad_arm_part: ['鼻托脚更换/补修', '便于按左右和形状补修需要部位', '用于更换或补修鼻托脚周边的部件。可按左右和安装形状选择，便于只补修需要的位置。'],
  screwdriver_handle: ['可换头螺丝刀柄', '便于按作业切换对应刀头', '与对应替换刀头组合使用的螺丝刀柄。可根据修理和调整内容切换刀头，便于整理工具。'],
};

templates.ko = {
  pliers_klings_adjustment: ['클링스/패드 다리 조정', '작은 각도를 잡아 코받침 착용감을 맞추기 쉬움', '클링스와 패드 다리의 미세한 각도 조정에 사용하는 플라이어입니다. 끝 모양에 맞춰 작은 부위를 안정적으로 잡아 코받침 착용감을 맞추기 쉽습니다.'],
  pliers_pad_box_adjustment: ['박스/원터치 패드 조정', '패드 금구를 안정적으로 잡기 쉬움', '박스형 또는 원터치식 코패드 조정에 사용하는 플라이어입니다. 패드 주변을 안정적으로 잡아 각도 조정과 교체 작업을 진행하기 쉽습니다.'],
  pliers_push_lock_pad_adjustment: ['푸시락 패드 조정', '흠집과 색 벗겨짐을 줄이며 조정하기 쉬움', '푸시락 패드 전용 조정 플라이어입니다. 금구를 점이 아닌 면으로 잡아 좁은 공간에서도 흠집과 색 벗겨짐을 줄이며 각도를 조정하기 쉽습니다.'],
  pliers_twin_pad_arm_adjustment: ['두 갈래 패드 다리 조정', '감싸는 부분의 풀림을 막으며 작업하기 쉬움', '두 갈래 패드 다리 전용 조정 플라이어입니다. 장착 금구와 패드를 감싸 잡아 조정 중 풀림을 줄이며 작업할 수 있습니다.'],
  pliers_built_in_pad_adjustment: ['나사 집기/빌트인 패드 조정', '작은 패드 금구를 안정적으로 잡기 쉬움', '나사 집기와 빌트인 패드 조정에 사용하는 플라이어입니다. 패드 주변의 작은 금구를 안정적으로 잡아 수리와 조정 작업을 진행하기 쉽습니다.'],
  pliers_joint_hold: ['지 부위 고정/템플 조정 보조', '지 부위를 고정해 템플 조정을 안정시키기 쉬움', '템플 조정 시 지 부위를 고정하는 플라이어입니다. 프레임을 안정적으로 잡아 각도 조정을 더 쉽게 할 수 있습니다.'],
  pliers_two_point_hold: ['투포인트 고정/템플 벌림 조정', '렌즈를 빼지 않고 템플 벌림을 조정하기 쉬움', '투포인트 프레임을 고정하고 템플 벌림을 조정하는 플라이어입니다. 렌즈를 빼지 않고 프레임을 잡아 작업 중 흔들림을 줄입니다.'],
  pliers_temple_angle: ['템플 각도/전경각 조정', '착용 위치와 시야 균형을 맞추기 쉬움', '템플 각도와 전경각을 조정하는 플라이어입니다. 얼굴 폭과 착용 위치에 맞춰 착용감과 시야 균형을 정돈하기 쉽습니다.'],
  pliers_temple_opening: ['템플 벌림 조정', '좌우 벌림과 착용감을 맞추기 쉬움', '템플의 벌림 정도를 조정하는 플라이어입니다. 좌우 벌림과 착용감을 확인하면서 프레임을 안정적으로 정돈하기 쉽습니다.'],
  pliers_bridge_angle: ['브리지 각도 조정', '프레임 전면 균형을 맞추기 쉬움', '브리지 각도 조정용 플라이어입니다. 좌우 렌즈 위치와 프레임 전면 균형을 정돈해 착용감 조정에 도움이 됩니다.'],
  pliers_modern_bending: ['모던 굽힘 조정', '힘을 한 지점에 집중해 굽히기 쉬움', '모던 굽힘 조정에 사용하는 플라이어입니다. 모던을 받친 뒤 쥐어 힘을 집중시켜 손으로 굽히기 어려운 부위도 조정하기 쉽습니다.'],
  pliers_rim_shape: ['림 형상 조정', '렌즈 맞춤을 위해 림 형태를 정돈하기 쉬움', '림의 아르 수정과 나일로르 형태 교정에 사용하는 플라이어입니다. 림 형상을 정돈해 렌즈 맞춤 정확도를 높이기 쉽습니다.'],
  pliers_rimless_screw_cutter: ['투포인트 나사 길이 조정', '나사를 필요한 길이로 자르기 쉬움', '투포인트 프레임용 나사 절단 플라이어입니다. 끝 구멍에 나사를 넣고 잘라 필요한 길이로 맞추기 쉽습니다.'],
  pliers_cutting: ['절단/끝 절단 작업', '작은 부품과 선재를 원하는 위치에서 처리하기 쉬움', '절단과 끝 절단 작업에 사용하는 공구입니다. 작은 부품이나 선재를 원하는 위치에서 처리해 수리와 가공 마무리에 도움이 됩니다.'],
  pliers_replacement_tip: ['플라이어 끝 교체/보호', '프레임과 부품의 흠집을 줄이기 쉬움', '대상 플라이어 끝에 장착하는 교체 부품입니다. 접촉면을 보호해 조정 중 프레임과 부품의 흠집을 줄이는 데 도움이 됩니다.'],
  pliers_guard_arm_install: ['가드 암 장착', '두 다리 부품을 잡아 압입하기 쉬움', '가드 암 같은 두 다리 부품을 잡아 장착하는 플라이어입니다. 가열과 압입 작업 중 부품 위치를 안정시키기 쉽습니다.'],
  pliers_generic: ['안경테 조정/부품 고정', '목표 부위를 안정적으로 잡기 쉬움', '안경테 조정과 부품 고정에 사용하는 플라이어입니다. 끝 모양에 맞춰 사용하면 목표 부위를 안정적으로 잡기 쉽습니다.'],
  processing_file: ['가공/연마', '세밀한 절삭과 마감 작업을 하기 쉬움', '안경테나 부품의 절삭과 마감에 사용하는 가공 용품입니다. 형상과 용도에 맞춰 선택하면 세밀한 조정과 연마 작업에 도움이 됩니다.'],
  pad_arm_part: ['코패드 다리 교체/보수', '필요한 쪽과 형상만 골라 보수하기 쉬움', '코패드 다리 주변을 교체하거나 보수하는 부품입니다. 좌우와 장착 형상에 맞춰 필요한 부분만 보수하기 쉽습니다.'],
  screwdriver_handle: ['교체식 드라이버 손잡이', '작업에 맞춰 호환 팁을 바꾸기 쉬움', '호환되는 교체 팁과 함께 사용하는 드라이버 손잡이입니다. 수리와 조정 내용에 맞춰 끝을 바꾸어 쓰기 쉽습니다.'],
};

function asObj(lang, key) {
  if (lang === 'ja') return templates.ja[key];
  const [usage, benefit, summary] = templates[lang][key];
  return { usage, benefit, summary };
}

function hasAny(text, words) {
  return words.some((w) => text.includes(w));
}

function detectTemplate(row, snippets) {
  const name = compact(row.商品名_JA || '');
  const existing = compact(row.一言要約_JA || '');
  const text = compact([name, snippets.join(' || ')].join(' '));
  const lowerCode = String(row.品番 || '').toLowerCase();

  const isPliers = /ヤットコ|ニッパー/.test(name) || /Plier|ヤットコ/.test(text);
  if (isPliers) {
    if (/先プラスチック|先ビニ|保護カバー|交換用|替/.test(name)) return 'pliers_replacement_tip';
    if (/ガード.*足|ガードアーム/.test(text)) return 'pliers_guard_arm_install';
    if (/ニッパー|喰い切り|カット/.test(name) || /切断|喰い切り/.test(text)) return 'pliers_cutting';
    if (/ネジ切り|ネジを差し込んで切|ネジ.*切/.test(text)) return 'pliers_rimless_screw_cutter';
    if (/ツーポイント固定|レンズを外さず/.test(text)) return 'pliers_two_point_hold';
    if (/クリングス|パット足/.test(text)) return 'pliers_klings_adjustment';
    if (/プッシュロック/.test(text)) return 'pliers_push_lock_pad_adjustment';
    if (/ダキ足|抱き足|抱き込み/.test(text)) return 'pliers_twin_pad_arm_adjustment';
    if (/ビルトイン|ネジ掴み/.test(text)) return 'pliers_built_in_pad_adjustment';
    if (/箱蝶|ボックス|ワンタッチ/.test(text)) return 'pliers_pad_box_adjustment';
    if (/パット調整|パッド調整|鼻パッド|パッド/.test(text)) return 'pliers_pad_box_adjustment';
    if (/智固定|智の部分|くぼみに智/.test(text)) return 'pliers_joint_hold';
    if (/モダン曲げ|モダンをあてがう|モダン.*曲げ/.test(text)) return 'pliers_modern_bending';
    if (/テンプル角度|前傾角/.test(text)) return 'pliers_temple_angle';
    if (/テンプル開き|テンプル開閉/.test(text)) return 'pliers_temple_opening';
    if (/ブリッジ角度/.test(text)) return 'pliers_bridge_angle';
    if (/リム.*アール|アール修正|ナイロール型直し|リム形状/.test(text)) return 'pliers_rim_shape';
    if (lowerCode === '104') return 'pliers_klings_adjustment';
    return 'pliers_generic';
  }

  const generic = existing.includes('眼鏡店の作業や店頭提案を補助する商品です');
  if (generic || row.説明カテゴリ === 'general') {
    if (/ヤスリ|砥石|磨き|研磨|バフ|ブラシ|穴広げ|溝削り|マンドレール|セル削り/.test(name)) return 'processing_file';
    if (/グースネック|U型|上付足|横付足|パット足|パッド足/.test(name + text)) return 'pad_arm_part';
    if (/ドライバ.*柄|ドライバー.*柄/.test(name)) return 'screwdriver_handle';
  }
  return '';
}

function shouldUpdate(row, templateKey) {
  if (!templateKey) return false;
  if (String(row.品番 || '') === '104') return true;
  const current = compact(row.一言要約_JA || '');
  const next = templates.ja[templateKey]?.summary || '';
  if (!next || current === next) return false;
  if (templateKey.startsWith('pliers_')) return /ヤットコ|ニッパー/.test(row.商品名_JA || '');
  return current.includes('眼鏡店の作業や店頭提案を補助する商品です') || row.説明カテゴリ === 'general';
}

function applyTemplate(row, templateKey) {
  for (const lang of ['ja', 'en', 'zh', 'ko']) {
    const t = asObj(lang, templateKey);
    const suffix = lang.toUpperCase();
    row[`一言要約_${suffix}`] = t.summary;
    row[`接客説明_${suffix}`] = t.summary;
    row[`用途_${suffix}`] = t.usage;
    row[`メリット_${suffix}`] = t.benefit;
  }
  row.説明カテゴリ = templateKey;
  row.説明強化元 = 'HP照合+カタログPDF抽出メモ+品番周辺文脈';
  if (String(row.品番 || '') === '104') {
    row.商品ページURL = 'https://www.san-nishimura.co.jp/product/item/?key_word=104';
  }
}

const text = fs.readFileSync(masterPath, 'utf8');
const { headers, objects } = rowsToObjects(parseCsv(text));
const auditRows = [];
let updated = 0;

for (const row of objects) {
  const snippets = findSnippets(row);
  const templateKey = detectTemplate(row, snippets);
  const oldSummary = row.一言要約_JA || '';
  const oldCategory = row.説明カテゴリ || '';
  const update = shouldUpdate(row, templateKey);
  if (update) {
    applyTemplate(row, templateKey);
    updated += 1;
  }
  auditRows.push({
    品番: row.品番,
    商品名: row.商品名_JA,
    HPから確認した情報: row.商品ページURL ? `商品ページURL: ${row.商品ページURL}` : '',
    カタログから確認した情報: snippets.join(' || '),
    日本語の一言要約: row.一言要約_JA,
    英語の一言要約: row.一言要約_EN,
    中国語の一言要約: row.一言要約_ZH,
    韓国語の一言要約: row.一言要約_KO,
    確認元URLまたはカタログ掲載ページ: [row.商品ページURL, row.カタログ参照].filter(Boolean).join(' / '),
    判定テンプレート: templateKey,
    更新有無: update ? 'updated' : 'kept',
    旧カテゴリ: oldCategory,
    旧日本語要約: oldSummary,
  });
}

fs.writeFileSync(masterPath, stringifyCsv(headers, objects), 'utf8');
fs.writeFileSync(auditPath, stringifyCsv(Object.keys(auditRows[0]), auditRows), 'utf8');

const counts = auditRows.reduce((acc, r) => {
  const key = r.判定テンプレート || 'none';
  acc[key] = (acc[key] || 0) + 1;
  return acc;
}, {});
console.log(JSON.stringify({ rows: objects.length, updated, auditPath, counts }, null, 2));
