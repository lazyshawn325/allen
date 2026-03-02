#!/usr/bin/env python3
"""
大学生外快小工具：计算净收入、时薪、月度目标缺口。

用法示例：
  python3 tools/sidehustle_calculator.py --income 3200 --cost 450 --hours 38 --goal 5000
"""

import argparse


def money(v: float) -> str:
    return f"¥{v:,.2f}"


def main() -> None:
    p = argparse.ArgumentParser(description="外快收益计算器")
    p.add_argument("--income", type=float, required=True, help="总收入")
    p.add_argument("--cost", type=float, default=0.0, help="总成本")
    p.add_argument("--hours", type=float, default=0.0, help="总耗时（小时）")
    p.add_argument("--goal", type=float, default=0.0, help="月目标收入")
    args = p.parse_args()

    net = args.income - args.cost
    hourly = (net / args.hours) if args.hours > 0 else 0.0
    gap = max(args.goal - net, 0.0) if args.goal > 0 else 0.0

    print("=== 外快收益报告 ===")
    print(f"收入: {money(args.income)}")
    print(f"成本: {money(args.cost)}")
    print(f"净收入: {money(net)}")
    if args.hours > 0:
        print(f"有效时薪: {money(hourly)}/小时")
    if args.goal > 0:
        if gap > 0:
            print(f"距离目标还差: {money(gap)}")
        else:
            print("已达成/超过目标 🎉")


if __name__ == "__main__":
    main()
