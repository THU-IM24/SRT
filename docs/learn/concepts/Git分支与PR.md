# Git分支与PR

**一句话**：分支是代码的一条“平行草稿线”，PR（Pull Request，合并请求）是请别人检查后把你的草稿并入正式版的申请。

**怎么用**：
1. `main` 是正式版。先 `git pull` 拿到最新的 main。
2. `git checkout -b 名字/任务` 新建自己的分支，在上面随便改，不影响别人。
3. `git add`、`git commit` 存档，`git push` 推到 GitHub。
4. 在 GitHub 上开 PR，另一个人看过点 Approve 后合并进 main。
5. 大家 `git pull`，就都拿到了你的成果。

**在本项目里**：main 受保护，不能直接推送，必须走 PR 并由推送者以外的人批准，这样谁都不会把正式代码弄坏。

**相关概念**：[SSH](SSH.md)
