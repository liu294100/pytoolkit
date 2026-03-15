// ================================
// Rule Generator Entry
// ================================
function main(config, profileName) {

  /**
   * ================================
   * 1️⃣ 政策分组
   * ================================
   */
  const ruleGroups = {
    "DIRECT": [
      // 示例 走直连 可以添加更多   
      "qq.com",
      "163.com"
    ],

    "🔰 手动选择": [
      // LinkedIn / Microsoft
      "linkedin.com",
      "licdn.com",
      "copilot.microsoft.com",

      // AWS
      "amazonaws.com",
      "aws.amazon.com",
      "freetier.us-east-1.api.aws",
      "secretsmanager.ap-east-1.amazonaws.com"
    ]
  };

  /**
   * ================================
   * 2️⃣ Gov 域名自动生成
   * ================================
   */

  // 常见国家 / 地区代码
  const govCountryCodes = [
    "cn", "hk", "mo", "tw",
    "sg", "jp", "kr",
    "uk", "fr", "de", "it", "es",
    "us", "ca",
    "au", "nz",
    "in", "id", "my", "th", "vn",
    "ph",
    "br", "mx",
    "za"
  ];

  // 特殊政府域（不是 gov.xx 结构）
  const specialGovDomains = [
    "gov",       // 通用
    "go.kr",     // 韩国
    "gob.mx",    // 墨西哥
    "gov.au",    // 澳大利亚
    "gov.uk",    // 英国（部分系统）
    "gov.za"     // 南非
  ];

  // 生成 gov.xx
  const govDomains = govCountryCodes.map(code => `gov.${code}`);

  // 合并并加入 DIRECT
  ruleGroups["DIRECT"].push(
    ...specialGovDomains,
    ...govDomains
  );

  /**
   * ================================
   * 3️⃣ 统一生成规则（去重 + 前置）
   * ================================
   */
  const generated = new Set();

  Object.entries(ruleGroups).forEach(([policy, domains]) => {
    domains.forEach(domain => {
      const rule = `DOMAIN-SUFFIX,${domain},${policy}`;
      if (!generated.has(rule)) {
        generated.add(rule);
        config.rules.unshift(rule);
      }
    });
  });

  return config;
}
